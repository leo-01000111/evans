"""
A Simulink model: blocks, connections, and the ``.fmdl`` file format.
=====================================================================
Deliberately separate from :class:`evans.core.model.Model`, which is the
single-port LTI graph the analysis half uses. A simulation block has several
typed ports and need not be linear, so it needs its own container —
:mod:`evans.sim.linearize` is the bridge between the two.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .block import Block, BlockError, create

FORMAT = "evans-model"
#: What the same format was called before the program was renamed (0.9).
#: Read, never written, so older .fmdl files keep opening.
LEGACY_FORMATS = ("fake" "matlab-model",)
VERSION = 1

#: A model's run settings, as Simulink names them, and their defaults.
#: ``MaxStep`` 0 means automatic; a fixed-step solver needs a positive one.
DEFAULT_SETTINGS: dict[str, Any] = {
    "StopTime": 10.0,
    "Solver": "ode45",
    "MaxStep": 0.0,
    "RelTol": 1e-6,
    "AbsTol": 1e-9,
}


@dataclass(frozen=True)
class PortRef:
    """One end of a wire: a block and one of its ports, by name."""
    block: str
    port: str

    def __str__(self) -> str:
        return f"{self.block}.{self.port}"


@dataclass(frozen=True)
class Connection:
    """A wire from an output port to an input port."""
    src: PortRef
    dst: PortRef

    def __str__(self) -> str:
        return f"{self.src} → {self.dst}"


@dataclass
class BlockPlacement:
    """
    Where a block sits on the canvas, and which way it faces. Ignored by
    the solver.

    ``rotation`` turns the block clockwise in quarter turns (0, 90, 180,
    270); ``flip`` mirrors it left to right first, so its inputs are on the
    right. Together they cover every way Simulink can point a block.
    """
    x: float = 0.0
    y: float = 0.0
    rotation: int = 0
    flip: bool = False


class ModelError(Exception):
    """The model is structurally invalid."""


class SimModel:
    """
    A block diagram that can be simulated.

    One input port takes at most one wire — fan-*in* is what a ``Sum`` block is
    for, and silently adding two signals together because they happened to
    land on the same port is the kind of thing that costs an afternoon. Fan-out
    is unrestricted: one output may drive any number of inputs.
    """

    def __init__(self, name: str = "untitled") -> None:
        self.name = name
        #: How the model runs: stop time, solver, step, tolerances.
        self.settings: dict[str, Any] = dict(DEFAULT_SETTINGS)
        self._blocks: dict[str, Block] = {}
        self._placements: dict[str, BlockPlacement] = {}
        self._connections: list[Connection] = []
        #: Text notes on the diagram: ``{"text", "x", "y"}`` each.
        self.annotations: list[dict[str, Any]] = []
        #: Signal names drawn on wires, by source port (``"block.port"``):
        #: every branch of a signal carries its name, as in Simulink.
        self.signal_names: dict[str, str] = {}
        #: Where a wire's bend was dragged to, by ``str(connection)``: the x
        #: of its vertical run (a forward wire), or the y of its return run
        #: (a feedback wire).
        self.bends: dict[str, float] = {}

    # ── blocks ──────────────────────────────────────────────────

    def add(self, type_name: str, block_id: str | None = None,
            x: float = 0.0, y: float = 0.0, **params: Any) -> Block:
        """Create and add a block, returning it."""
        block_id = block_id or self._unique_id(type_name)
        if block_id in self._blocks:
            raise ModelError(f"duplicate block id {block_id!r}")
        block = create(type_name, block_id, **params)
        self._blocks[block_id] = block
        self._placements[block_id] = BlockPlacement(x, y)
        return block

    def add_block(self, block: Block, x: float = 0.0, y: float = 0.0) -> Block:
        if block.block_id in self._blocks:
            raise ModelError(f"duplicate block id {block.block_id!r}")
        self._blocks[block.block_id] = block
        self._placements[block.block_id] = BlockPlacement(x, y)
        return block

    def remove(self, block_id: str) -> None:
        """Delete a block and every wire touching it."""
        if block_id not in self._blocks:
            raise ModelError(f"no block {block_id!r}")
        del self._blocks[block_id]
        self._placements.pop(block_id, None)
        for conn in self._connections:
            if block_id in (conn.src.block, conn.dst.block):
                self.bends.pop(str(conn), None)
        self._connections = [
            c for c in self._connections
            if c.src.block != block_id and c.dst.block != block_id
        ]
        self.signal_names = {ref: name for ref, name in
                             self.signal_names.items()
                             if ref.split(".")[0] != block_id}

    def _unique_id(self, type_name: str) -> str:
        i = 1
        while f"{type_name}{i}" in self._blocks:
            i += 1
        return f"{type_name}{i}"

    # ── connections ─────────────────────────────────────────────

    def connect(self, src: str, dst: str) -> Connection:
        """
        Wire ``"block.port"`` to ``"block.port"``.

        The port may be omitted when the block has exactly one of that kind,
        so ``connect("Step1", "Gain1")`` works for the common case.
        """
        src_ref = self._resolve(src, kind="output")
        dst_ref = self._resolve(dst, kind="input")

        existing = self.connection_into(dst_ref)
        if existing is not None:
            raise ModelError(
                f"{dst_ref} already has a wire from {existing.src}. "
                f"An input port takes one signal — use a Sum block to "
                f"combine two."
            )
        conn = Connection(src_ref, dst_ref)
        self._connections.append(conn)
        return conn

    def disconnect(self, conn: Connection) -> None:
        self._connections = [c for c in self._connections if c != conn]
        self.bends.pop(str(conn), None)

    def _resolve(self, spec: str, kind: str) -> PortRef:
        if "." in spec:
            block_id, port = spec.split(".", 1)
        else:
            block_id, port = spec, None

        block = self._blocks.get(block_id)
        if block is None:
            raise ModelError(
                f"no block {block_id!r}. Have: "
                f"{', '.join(sorted(self._blocks)) or '(none)'}"
            )
        ports = block.outputs if kind == "output" else block.inputs
        if port is None:
            if len(ports) != 1:
                raise ModelError(
                    f"{block_id} has {len(ports)} {kind} ports "
                    f"({', '.join(ports) or 'none'}); name one explicitly, "
                    f"e.g. '{block_id}.{ports[0] if ports else 'port'}'"
                )
            port = ports[0]
        elif port not in ports:
            raise ModelError(
                f"{block_id} has no {kind} port {port!r}; "
                f"valid: {', '.join(ports) or '(none)'}"
            )
        return PortRef(block_id, port)

    def connection_into(self, ref: PortRef) -> Connection | None:
        for c in self._connections:
            if c.dst == ref:
                return c
        return None

    def connections_from(self, ref: PortRef) -> list[Connection]:
        return [c for c in self._connections if c.src == ref]

    # ── introspection ───────────────────────────────────────────

    @property
    def blocks(self) -> dict[str, Block]:
        return dict(self._blocks)

    @property
    def connections(self) -> list[Connection]:
        return list(self._connections)

    def block(self, block_id: str) -> Block:
        try:
            return self._blocks[block_id]
        except KeyError:
            raise ModelError(f"no block {block_id!r}") from None

    def placement(self, block_id: str) -> BlockPlacement:
        return self._placements.get(block_id, BlockPlacement())

    def move(self, block_id: str, x: float, y: float) -> None:
        place = self.placement(block_id)
        self._placements[block_id] = BlockPlacement(x, y, place.rotation,
                                                    place.flip)

    def orient(self, block_id: str, rotation: int | None = None,
               flip: bool | None = None) -> None:
        """Turn or mirror a block; the other setting is kept."""
        place = self.placement(block_id)
        if rotation is not None:
            if rotation % 90:
                raise ModelError("a block turns in quarter turns")
            place.rotation = int(rotation) % 360
        if flip is not None:
            place.flip = bool(flip)
        self._placements[block_id] = place

    def blocks_of_type(self, type_name: str) -> list[Block]:
        return [b for b in self._blocks.values() if b.type_name == type_name]

    def unconnected_inputs(self) -> list[PortRef]:
        """Input ports with no wire — they read zero, which is worth a warning."""
        missing = []
        for block in self._blocks.values():
            for port in block.inputs:
                ref = PortRef(block.block_id, port)
                if self.connection_into(ref) is None:
                    missing.append(ref)
        return missing

    def __iter__(self) -> Iterator[Block]:
        return iter(self._blocks.values())

    def __len__(self) -> int:
        return len(self._blocks)

    def __repr__(self) -> str:
        return (f"<SimModel {self.name!r}: {len(self._blocks)} blocks, "
                f"{len(self._connections)} connections>")

    # ── persistence ─────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return {
            "format": FORMAT,
            "version": VERSION,
            "name": self.name,
            "settings": dict(self.settings),
            "blocks": [self._block_entry(b) for b in self._blocks.values()],
            "connections": [
                {"src": str(c.src), "dst": str(c.dst),
                 **({"bend": self.bends[str(c)]} if str(c) in self.bends
                    else {})}
                for c in self._connections
            ],
            **({"annotations": [dict(a) for a in self.annotations]}
               if self.annotations else {}),
            **({"signal_names": dict(self.signal_names)}
               if self.signal_names else {}),
        }

    def _block_entry(self, b: Block) -> dict[str, Any]:
        place = self.placement(b.block_id)
        entry = {
            "id": b.block_id,
            "type": b.type_name,
            "params": _jsonable(b.raw_params()),
            "x": place.x,
            "y": place.y,
        }
        # Only when not the default, so an unturned model reads as before.
        if place.rotation:
            entry["rotation"] = place.rotation
        if place.flip:
            entry["flip"] = True
        return entry

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SimModel:
        if data.get("format") not in (FORMAT, *LEGACY_FORMATS):
            raise ModelError(
                f"not an Evans model file (format={data.get('format')!r})")
        if data.get("version", 1) > VERSION:
            raise ModelError(
                f"model was written by a newer version "
                f"(file format {data['version']}, this build reads {VERSION})")

        model = cls(data.get("name", "untitled"))
        for key, value in (data.get("settings") or {}).items():
            if key in DEFAULT_SETTINGS:
                model.settings[key] = value
        for entry in data.get("blocks", []):
            try:
                model.add(entry["type"], entry["id"],
                          x=entry.get("x", 0.0), y=entry.get("y", 0.0),
                          **entry.get("params", {}))
                if entry.get("rotation") or entry.get("flip"):
                    model.orient(entry["id"], int(entry.get("rotation", 0)),
                                 bool(entry.get("flip", False)))
            except (BlockError, KeyError) as exc:
                raise ModelError(
                    f"could not load block {entry.get('id', '?')!r} "
                    f"of type {entry.get('type', '?')!r}: {exc}"
                ) from exc
        for entry in data.get("connections", []):
            try:
                conn = model.connect(entry["src"], entry["dst"])
            except (ModelError, KeyError) as exc:
                raise ModelError(
                    f"could not connect {entry.get('src')} → "
                    f"{entry.get('dst')}: {exc}"
                ) from exc
            if "bend" in entry:
                model.bends[str(conn)] = float(entry["bend"])
        model.annotations = [
            {"text": str(a.get("text", "")), "x": float(a.get("x", 0.0)),
             "y": float(a.get("y", 0.0))}
            for a in data.get("annotations", [])]
        model.signal_names = {str(k): str(v) for k, v in
                              (data.get("signal_names") or {}).items()}
        return model

    def save(self, path: str | Path) -> None:
        """Write the model; as in Simulink, it takes the file's name."""
        self.name = Path(path).stem
        Path(path).write_text(json.dumps(self.to_dict(), indent=2),
                              encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> SimModel:
        model = cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
        model.name = Path(path).stem
        return model

    def copy(self) -> SimModel:
        return SimModel.from_dict(self.to_dict())


def _jsonable(params: dict[str, Any]) -> dict[str, Any]:
    """Convert numpy values to plain Python so the model round-trips as JSON."""
    import numpy as np

    out: dict[str, Any] = {}
    for key, value in params.items():
        if isinstance(value, np.ndarray):
            out[key] = value.tolist()
        elif isinstance(value, (np.floating, np.integer)):
            out[key] = value.item()
        else:
            out[key] = value
    return out
