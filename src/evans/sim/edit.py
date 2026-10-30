"""
Edits that restructure a model: grouping blocks into a subsystem.

Kept apart from the canvas so it can be tested on a model alone, and so the
console could use it too. The canvas wraps it in an undoable command.
"""

from __future__ import annotations

from .model import ModelError, PortRef, SimModel


def group_into_subsystem(model: SimModel, block_ids, name: str | None = None
                         ) -> str:
    """
    Replace ``block_ids`` with one Subsystem holding them; return its id.

    Wires inside the selection move in with the blocks. Each signal that
    enters the selection gets an Inport (one per source, however many blocks
    inside it feeds), and each that leaves gets an Outport (one per source
    inside, however many blocks outside it feeds), so the model computes
    exactly what it did before. Ports are ordered top to bottom, as the
    blocks they serve sit.
    """
    ids = [b for b in dict.fromkeys(block_ids)]
    if not ids:
        raise ModelError("select the blocks to put in the subsystem")
    for bid in ids:
        model.block(bid)                    # raises for an unknown id
    chosen = set(ids)

    inner = SimModel(name or "Subsystem")
    for bid in ids:
        block = model.block(bid)
        place = model.placement(bid)
        inner.add(block.type_name, bid, x=place.x, y=place.y,
                  **block.raw_params())
        inner.orient(bid, place.rotation, place.flip)

    entering: dict[PortRef, list[PortRef]] = {}     # outside source → inside
    leaving: dict[PortRef, list[PortRef]] = {}      # inside source → outside
    for conn in model.connections:
        src_in, dst_in = conn.src.block in chosen, conn.dst.block in chosen
        if src_in and dst_in:
            inner.connect(str(conn.src), str(conn.dst))
            bend = model.bends.get(str(conn))
            if bend is not None:
                inner.bends[str(conn)] = bend
        elif dst_in:
            entering.setdefault(conn.src, []).append(conn.dst)
        elif src_in:
            leaving.setdefault(conn.src, []).append(conn.dst)

    for ref, label in model.signal_names.items():
        if ref.split(".")[0] in chosen:
            inner.signal_names[ref] = label

    xs = [model.placement(b).x for b in ids]
    ys = [model.placement(b).y for b in ids]
    left, right = min(xs), max(xs)

    def by_height(item):
        refs = item[1]
        return min(model.placement(r.block).y for r in refs)

    inport_names: dict[PortRef, str] = {}
    for n, (src, targets) in enumerate(
            sorted(entering.items(), key=by_height), start=1):
        port_id = _fresh(inner, f"In{n}")
        y = min(model.placement(t.block).y for t in targets)
        inner.add("Inport", port_id, x=left - 160, y=y,
                  port_name=f"in{n}", order=n)
        for target in targets:
            inner.connect(port_id, str(target))
        inport_names[src] = f"in{n}"

    outport_names: dict[PortRef, str] = {}
    for n, (src, _targets) in enumerate(
            sorted(leaving.items(),
                   key=lambda item: model.placement(item[0].block).y),
            start=1):
        port_id = _fresh(inner, f"Out{n}")
        inner.add("Outport", port_id, x=right + 160,
                  y=model.placement(src.block).y,
                  port_name=f"out{n}", order=n)
        inner.connect(str(src), port_id)
        outport_names[src] = f"out{n}"

    sub_id = _fresh(model, name or "Subsystem")
    for bid in ids:
        model.remove(bid)
    sub = model.add("Subsystem", sub_id, x=sum(xs) / len(xs),
                    y=sum(ys) / len(ys), name=name or sub_id)
    sub.set_inner(inner)
    for src, port in inport_names.items():
        model.connect(str(src), f"{sub_id}.{port}")
    for src, port in outport_names.items():
        for target in leaving[src]:
            model.connect(f"{sub_id}.{port}", str(target))
        label = model.signal_names.pop(str(src), None) \
            or inner.signal_names.get(str(src))
        if label:
            model.signal_names[f"{sub_id}.{port}"] = label
    return sub_id


def _fresh(model: SimModel, stem: str) -> str:
    """``stem``, or ``stem2``, ``stem3`` … whichever is free."""
    if stem not in model.blocks:
        return stem
    n = 2
    while f"{stem}{n}" in model.blocks:
        n += 1
    return f"{stem}{n}"
