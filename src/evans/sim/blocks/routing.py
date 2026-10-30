"""
Signals passed by name: Goto/From, and data stores.

None of these blocks runs. :func:`resolve_links` replaces each ``From`` (or
``DataStoreRead``) with a wire from whatever drives the matching ``Goto``
(or ``DataStoreWrite``) when the model compiles, so a model that passes a
signal by name runs exactly as if it had been wired by hand, algebraic-loop
check and all.

A Goto's tag is **local** (seen by Froms in the same subsystem only) or
**global** (seen everywhere), as in Simulink. A data store is global: a
``DataStoreMemory`` declares it and its initial value, at most one
``DataStoreWrite`` sets it, and every ``DataStoreRead`` reads it. Simulink
orders data store reads and writes by block priority within a step; Evans
reads the written signal directly, so a read that feeds its own write is an
algebraic loop and is reported as one, to be broken with a delay.
"""

from __future__ import annotations

import numpy as np

from ..block import Block, BlockError, ParamSpec, register

_CAT = "Signal Routing"


class _Dissolved(Block):
    """A block that the compiler replaces by a wire before anything runs."""

    def output(self, t, x, xd, u):
        raise BlockError(
            f"{self.type_name} {self.block_id!r} reached the solver; it "
            f"should have been replaced by a wire when the model compiled")


@register
class Goto(_Dissolved):
    type_name = "Goto"
    category = _CAT
    description = "Send a signal to the From blocks with the same tag."
    default_outputs = ()
    params_spec = (
        ParamSpec("tag", "Tag", "A", kind="str"),
        ParamSpec("visibility", "Visibility", "local", kind="choice",
                  choices=("local", "global")),
    )

    def output_widths(self, input_widths):
        return []

    def label(self):
        tag = self.params["tag"]
        return f"[{tag}]" if self.params["visibility"] == "local" \
            else "{" + tag + "}"


@register
class From(_Dissolved):
    type_name = "From"
    category = _CAT
    description = "Receive the signal of the Goto block with the same tag."
    default_inputs = ()
    params_spec = (ParamSpec("tag", "Tag", "A", kind="str"),)

    def label(self):
        return f"[{self.params['tag']}]"


@register
class DataStoreMemory(_Dissolved):
    type_name = "DataStoreMemory"
    category = _CAT
    description = "Declare a data store and its initial value."
    default_inputs = ()
    default_outputs = ()
    params_spec = (
        ParamSpec("store", "Data store name", "A", kind="str"),
        ParamSpec("initial", "Initial value", 0.0),
    )

    def output_widths(self, input_widths):
        return []

    def label(self):
        return f"store\n{self.params['store']}"


@register
class DataStoreWrite(_Dissolved):
    type_name = "DataStoreWrite"
    category = _CAT
    description = "Write a signal to a data store."
    default_outputs = ()
    params_spec = (ParamSpec("store", "Data store name", "A", kind="str"),)

    def output_widths(self, input_widths):
        return []

    def label(self):
        return f"write\n{self.params['store']}"


@register
class DataStoreRead(_Dissolved):
    type_name = "DataStoreRead"
    category = _CAT
    description = "Read a data store's value."
    default_inputs = ()
    params_spec = (ParamSpec("store", "Data store name", "A", kind="str"),)

    def label(self):
        return f"read\n{self.params['store']}"


LINK_TYPES = frozenset({"Goto", "From", "DataStoreMemory", "DataStoreWrite",
                        "DataStoreRead"})


def resolve_links(model):
    """
    ``model`` (flattened) with every Goto/From and data store wired through.

    Returns a new model, or ``model`` itself when it has none of them.
    Raises :class:`~evans.sim.compile.CompileError` for a From with no Goto,
    two Gotos with one tag in one scope, two writers to one store, or a read
    of a store that was never declared.
    """
    from ..compile import CompileError
    from ..model import PortRef, SimModel

    links = [b for b in model if b.type_name in LINK_TYPES]
    if not links:
        return model

    def scope(block_id: str) -> str:
        return block_id.rsplit("/", 1)[0] + "/" if "/" in block_id else "/"

    def driver(block) -> PortRef | None:
        conn = model.connection_into(PortRef(block.block_id, block.inputs[0]))
        return conn.src if conn is not None else None

    # ── Goto / From ──
    gotos: dict[tuple[str, str], Block] = {}
    for block in links:
        if block.type_name != "Goto":
            continue
        tag = block.params["tag"]
        key = (tag, "" if block.params["visibility"] == "global"
               else scope(block.block_id))
        if key in gotos:
            raise CompileError(
                f"Goto blocks {gotos[key].block_id!r} and {block.block_id!r} "
                f"both send the tag {tag!r} to the same From blocks; rename "
                f"one of them")
        gotos[key] = block

    source: dict[str, PortRef | None] = {}       # From/Read → what drives it
    constant: dict[str, float] = {}              # unwritten Read → its value
    for block in links:
        if block.type_name == "From":
            tag = block.params["tag"]
            goto = gotos.get((tag, scope(block.block_id))) \
                or gotos.get((tag, ""))
            if goto is None:
                raise CompileError(
                    f"From {block.block_id!r} reads the tag {tag!r}, and no "
                    f"Goto in its subsystem (or a global one) sends it")
            source[block.block_id] = driver(goto)

    # ── data stores ──
    memories = {b.params["store"]: b for b in links
                if b.type_name == "DataStoreMemory"}
    writers: dict[str, Block] = {}
    for block in links:
        if block.type_name == "DataStoreWrite":
            name = block.params["store"]
            if name in writers:
                raise CompileError(
                    f"Data store {name!r} is written by both "
                    f"{writers[name].block_id!r} and {block.block_id!r}; "
                    f"Evans allows one writer per store")
            writers[name] = block
    for block in links:
        if block.type_name != "DataStoreRead":
            continue
        name = block.params["store"]
        if name not in memories:
            raise CompileError(
                f"DataStoreRead {block.block_id!r} reads {name!r}, which no "
                f"Data Store Memory block declares")
        if name in writers:
            source[block.block_id] = driver(writers[name])
        else:
            constant[block.block_id] = float(np.asarray(
                memories[name].params["initial"], dtype=float).reshape(-1)[0])

    def follow(ref: PortRef | None) -> PortRef | None:
        """Through a From that a Goto fed from another From, and so on."""
        seen: set[str] = set()
        while ref is not None and ref.block in source \
                and ref.block not in seen:
            seen.add(ref.block)
            ref = source[ref.block]
        return ref

    flat = SimModel(model.name)
    flat.settings = dict(model.settings)
    for block in model:
        place = model.placement(block.block_id)
        if block.block_id in constant:
            flat.add("Constant", block.block_id, x=place.x, y=place.y,
                     value=constant[block.block_id])
        elif block.type_name not in LINK_TYPES:
            flat.add_block(block, place.x, place.y)

    for conn in model.connections:
        if model.block(conn.dst.block).type_name in LINK_TYPES:
            continue
        src: PortRef | None = conn.src
        if src.block in constant:
            src = PortRef(src.block, "out")
        elif src.block in source:
            src = follow(src)
        if src is None:
            continue                        # an unwired Goto: reads zero
        flat.connect(f"{src.block}.{src.port}",
                     f"{conn.dst.block}.{conn.dst.port}")
    return flat
