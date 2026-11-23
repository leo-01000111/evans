"""
The editing canvas.
===================
Drag blocks from the palette, wire ports together, move, delete, copy, paste,
undo. The model is the source of truth: every edit goes through a
:class:`~PySide6.QtGui.QUndoCommand` that mutates the
:class:`~evans.sim.model.SimModel`, after which the scene is rebuilt from
it. The drawing therefore cannot drift out of step with what will actually be
simulated.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QLineF, QPoint, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QKeySequence, QPainter, QPainterPath, QPen, QUndoStack
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsView,
    QMenu,
)

from ...sim.block import block_types, create
from ...sim.compile import CompileError, compile_model
from ...sim.linearize import LinearizationError, plant_seen_by
from ...sim.model import ModelError, PortRef, SimModel
from .. import theme
from . import commands as cmd
from .items import (
    GRID,
    AnnotationItem,
    BlockItem,
    PortItem,
    WireItem,
    hover_colour,
    snap,
)

MIME_TYPE = "application/x-evans-blocks"

#: What a refused edit says while a simulation runs (R6d).
LOCKED_MESSAGE = ("The model is locked while a simulation is running. "
                  "Press Stop, or wait for it to finish, to edit.")

#: The canvas's standing hint (its tooltip over empty canvas).
HINT = "Double-click or type to add a block. Drag from a port to wire it."
#: A wire dropped this far (view pixels) from its port counts as dropped.
DROP_DISTANCE = 12.0


class _LockableStack(QUndoStack):
    """
    The undo stack, refusing every change while its canvas is locked.

    All model edits go through ``push``, ``undo`` or ``redo``, so this is the
    one place a locked canvas cannot be bypassed; the canvas's gestures also
    check first, so they do not start something they cannot finish.
    """

    def __init__(self, canvas: SimCanvas) -> None:
        super().__init__(canvas)
        self._canvas = canvas

    def push(self, command) -> None:
        if self._canvas.locked:
            self._canvas.refuse_edit(redraw=True)
            return
        super().push(command)

    def undo(self) -> None:
        if self._canvas.locked:
            self._canvas.refuse_edit()
            return
        super().undo()

    def redo(self) -> None:
        if self._canvas.locked:
            self._canvas.refuse_edit()
            return
        super().redo()


class SimCanvas(QGraphicsView):
    """Editable block-diagram canvas."""

    model_changed = Signal()
    #: A different model was put on the canvas (not an edit of this one).
    model_replaced = Signal()
    selection_changed = Signal(object)      # BlockItem | None
    status = Signal(str)
    path_changed = Signal(list)             # breadcrumb, outermost first
    files_dropped = Signal(list)            # local files dropped on the canvas
    #: A Scope block was double-clicked: its path from the top level
    #: (``"Scope1"``, ``"Sub/Scope1"``), as a run result keys its signals.
    scope_requested = Signal(str)

    def __init__(self, model: SimModel | None = None, parent=None) -> None:
        super().__init__(parent)
        self.model = model or SimModel("untitled")
        #: True while a simulation runs: the model is read-only (R6d).
        self.locked = False
        self.undo_stack = _LockableStack(self)
        self.undo_stack.setUndoLimit(200)
        #: Reads block parameters written as workspace expressions; the app
        #: sets it to the console's (see :mod:`evans.sim.workspace`).
        self.evaluate = None

        self._scene = QGraphicsScene(self)
        self._scene.setSceneRect(-2000, -2000, 4000, 4000)
        self.setScene(self._scene)
        self.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

        #: Stack of (parent model, subsystem block id, parent undo stack) for
        #: each level we have descended into.
        self._stack: list[tuple[SimModel, str, QUndoStack]] = []
        self._blocks: dict[str, BlockItem] = {}
        self._wires: list[WireItem] = []
        self._pending_port: PortItem | None = None
        self._rubber_wire = None
        #: Dashed alignment lines shown while a block is being dragged.
        self._guides: list = []
        #: Where a middle-button pan last was, in view pixels; None if none.
        self._pan_from = None
        #: The last mouse position over the viewport, for where typing opens
        #: the quick insert; None when the mouse is elsewhere.
        self._last_mouse: QPoint | None = None
        #: The quick-insert popup (built on first use) and what it is for:
        #: the scene point to insert at, and the wire it was opened from.
        self._quick = None
        self._quick_scene_pos = QPointF()
        self._quick_wire: tuple[str, str, bool] | None = None
        self.viewport().setToolTip(HINT)

        self._scene.selectionChanged.connect(self._on_selection)
        theme.notifier().changed.connect(lambda *_: self._scene.update())
        from . import shapes
        shapes.notifier().changed.connect(lambda *_: self._scene.update())
        self.rebuild()

    # ── run lock ────────────────────────────────────────────────

    def set_locked(self, locked: bool) -> None:
        """Make the model read-only (a run is on) or editable again."""
        self.locked = locked
        self._cancel_wire()
        if self._quick is not None:
            self._quick.hide()
        self._apply_lock()

    def _apply_lock(self) -> None:
        for item in self._scene.items():
            if isinstance(item, (BlockItem, AnnotationItem)):
                item.setFlag(QGraphicsItem.ItemIsMovable, not self.locked)

    def refuse_edit(self, redraw: bool = False) -> None:
        """Say why an edit did nothing; ``redraw`` undoes a half-made one."""
        self.status.emit(LOCKED_MESSAGE)
        if redraw:
            QTimer.singleShot(0, self.rebuild)

    # ── model ↔ scene ───────────────────────────────────────────

    def set_model(self, model: SimModel) -> None:
        self.model = model
        self._stack.clear()
        self.undo_stack.clear()
        self.rebuild()
        self.model_changed.emit()
        self.model_replaced.emit()

    def restore_model(self, data: dict) -> None:
        """
        Replace the model wholesale — used by undo/redo.

        The run settings are not part of the history: undoing a block move
        must not also put back the stop time it was made under.
        """
        settings = self.model.settings
        self.model = SimModel.from_dict(data)
        self.model.settings = settings
        self.rebuild()
        self.model_changed.emit()

    def rebuild(self) -> None:
        """Redraw the scene from the model."""
        selected = {i.block_id for i in self._scene.selectedItems()
                    if isinstance(i, BlockItem)}
        self._scene.blockSignals(True)
        self._scene.clear()
        self._blocks.clear()
        self._wires.clear()
        self._pending_port = None
        self._rubber_wire = None
        self._guides = []           # the scene just deleted them

        for block in self.model:
            place = self.model.placement(block.block_id)
            item = BlockItem(block, place.x, place.y, place.rotation,
                             place.flip)
            item.moved.connect(self._on_block_moved)
            item.double_clicked.connect(self._edit_params)
            item.guides_changed.connect(self._show_guides)
            self._scene.addItem(item)
            self._blocks[block.block_id] = item
            if block.block_id in selected:
                item.setSelected(True)

        for conn in self.model.connections:
            src = self._port_item(conn.src, is_input=False)
            dst = self._port_item(conn.dst, is_input=True)
            if src is None or dst is None:
                continue
            wire = WireItem(conn, src, dst,
                            bend=self.model.bends.get(str(conn)),
                            label=self.model.signal_names.get(str(conn.src),
                                                              ""))
            wire.bend_moved.connect(self._on_bend_moved)
            self._scene.addItem(wire)
            self._wires.append(wire)

        for index, note in enumerate(self.model.annotations):
            item = AnnotationItem(index, note["text"], note["x"], note["y"])
            item.moved.connect(self._on_note_moved)
            item.double_clicked.connect(self.edit_annotation)
            self._scene.addItem(item)

        self._scene.blockSignals(False)
        self._apply_lock()
        self.validate()
        self.model_changed.emit()

    def _port_item(self, ref: PortRef, is_input: bool) -> PortItem | None:
        item = self._blocks.get(ref.block)
        return item.ports.get((ref.port, is_input)) if item else None

    # ── validation ──────────────────────────────────────────────

    def validate(self) -> str:
        """
        Compile the whole model and mark any block the compiler complains about.

        Validation runs after every edit, so a mistake shows up when it is
        made rather than when Run is pressed. It always compiles the *root*
        model: a subsystem viewed on its own has bare Inport/Outport blocks
        and no context, so compiling only what is on screen would report
        problems that do not exist and miss loops that close outside.
        """
        for item in self._blocks.values():
            item.set_error("")
        if len(self.model) == 0:
            return ""

        prefix = self._flat_prefix()
        try:
            compiled = compile_model(self.root_model(), self.evaluate)
        except CompileError as exc:
            message = str(exc)
            self._mark(message, message, prefix)
            return message

        if compiled.has_algebraic_loop:
            from ...sim.compile import describe_algebraic_loop
            message = describe_algebraic_loop(compiled)
            self._mark(" ".join(compiled.algebraic_loop), message, prefix)
            return message
        return ""

    def _flat_prefix(self) -> str:
        """How the blocks on screen are named once the model is flattened."""
        return "".join(f"{block_id}/" for _m, block_id, _s in self._stack)

    def _mark(self, haystack: str, message: str, prefix: str) -> None:
        for bid, item in self._blocks.items():
            if prefix + bid in haystack or (not prefix and bid in haystack):
                item.set_error(message)

    # ── editing ─────────────────────────────────────────────────

    def add_block(self, type_name: str, pos: QPointF | None = None) -> None:
        if self.locked:
            self.refuse_edit()
            return
        where = pos or self._free_spot()
        self.undo_stack.push(
            cmd.AddBlock(self, type_name, snap(where.x()), snap(where.y())))

    def _free_spot(self) -> QPointF:
        centre = self.mapToScene(self.viewport().rect().center())
        return QPointF(snap(centre.x()), snap(centre.y()))

    def _on_block_moved(self, block_id: str, x: float, y: float) -> None:
        self.undo_stack.push(cmd.MoveBlock(self, block_id, x, y))

    def _show_guides(self, guides: list) -> None:
        """
        Draw the dashed lines that explain a snap, replacing the last set.

        They live in the scene only while the drag lasts; the release clears
        them. They are drawn each move rather than diffed, because there are
        at most a handful and a stale guide is worse than a redundant redraw.
        """
        for line in self._guides:
            self._scene.removeItem(line)
        self._guides = []
        pen = QPen(hover_colour(), 1.0, Qt.DashLine)
        pen.setCosmetic(True)
        for guide in guides:
            lo, hi = guide.lo - 24.0, guide.hi + 24.0
            geometry = (QLineF(lo, guide.coord, hi, guide.coord)
                        if guide.orientation == "h"
                        else QLineF(guide.coord, lo, guide.coord, hi))
            line = self._scene.addLine(geometry, pen)
            line.setZValue(6)
            line.setAcceptedMouseButtons(Qt.NoButton)
            self._guides.append(line)

    def delete_selection(self) -> None:
        blocks = [i.block_id for i in self._scene.selectedItems()
                  if isinstance(i, BlockItem)]
        wires = [i.connection for i in self._scene.selectedItems()
                 if isinstance(i, WireItem)]
        notes = [i.index for i in self._scene.selectedItems()
                 if isinstance(i, AnnotationItem)]
        if self.locked:
            self.refuse_edit()
            return
        if blocks or wires or notes:
            self.undo_stack.push(cmd.DeleteSelection(self, blocks, wires,
                                                     notes))

    # ── turning, grouping, naming ───────────────────────────────

    def _edit(self, text: str, change) -> None:
        self.undo_stack.push(cmd.ModelEdit(self, text, change))

    def rotate_selection(self) -> int:
        """Turn the selected blocks a quarter turn clockwise."""
        ids = [b.block_id for b in self.selected_blocks()]
        if ids:
            def turn(model):
                for bid in ids:
                    model.orient(bid, model.placement(bid).rotation + 90)
            self._edit(f"rotate {len(ids)} block(s)", turn)
        return len(ids)

    def flip_selection(self) -> int:
        """Mirror the selected blocks left to right."""
        ids = [b.block_id for b in self.selected_blocks()]
        if ids:
            def mirror(model):
                for bid in ids:
                    model.orient(bid, flip=not model.placement(bid).flip)
            self._edit(f"flip {len(ids)} block(s)", mirror)
        return len(ids)

    def create_subsystem(self, name: str | None = None) -> str | None:
        """Put the selected blocks in a new subsystem, rewired to match."""
        from ...sim.edit import group_into_subsystem

        ids = [b.block_id for b in self.selected_blocks()]
        if not ids:
            self.status.emit("Select the blocks to put in a subsystem")
            return None
        made: list[str] = []
        self._edit(f"create subsystem from {len(ids)} block(s)",
                   lambda model: made.append(
                       group_into_subsystem(model, ids, name)))
        if made:
            self.status.emit(f"Grouped {len(ids)} block(s) into {made[0]}")
        return made[0] if made else None

    def ungroup_subsystem(self, block_id: str | None = None) -> bool:
        """Expand a subsystem back into its parent; False if it is refused."""
        from ...sim.edit import check_ungroup, ungroup_subsystem
        from ...sim.model import ModelError

        if block_id is None:
            subs = [b.block_id for b in self.selected_blocks()
                    if b.type_name == "Subsystem"]
            if len(subs) != 1:
                self.status.emit("Select one subsystem to expand")
                return False
            block_id = subs[0]
        try:
            check_ungroup(self.model, block_id)
        except ModelError as exc:
            self.status.emit(str(exc))
            return False
        self._edit(f"expand subsystem {block_id}",
                   lambda model: ungroup_subsystem(model, block_id))
        self.status.emit(f"Expanded {block_id}")
        return True

    def name_signal(self, conn, name: str | None = None) -> None:
        """Label the signal a wire carries; an empty name removes the label."""
        key = str(conn.src)
        if name is None:
            from PySide6.QtWidgets import QInputDialog
            name, ok = QInputDialog.getText(
                self, "Signal name", f"Name for {key}:",
                text=self.model.signal_names.get(key, ""))
            if not ok:
                return
        name = name.strip()

        def label(model):
            if name:
                model.signal_names[key] = name
            else:
                model.signal_names.pop(key, None)
        self._edit(f"name {key}", label)

    def _on_bend_moved(self, conn, value: float) -> None:
        def bend(model):
            model.bends[str(conn)] = value
        self._edit("move wire", bend)

    def straighten(self, conn) -> None:
        """Put a wire's bend back where the router puts it."""
        self._edit("reset wire", lambda model: model.bends.pop(str(conn),
                                                                  None))

    def add_annotation(self, pos: QPointF | None = None,
                       text: str | None = None) -> None:
        """A text note at ``pos`` (the view's centre by default)."""
        if text is None:
            from PySide6.QtWidgets import QInputDialog
            text, ok = QInputDialog.getMultiLineText(self, "Note", "Text:")
            if not ok:
                return
        if not text.strip():
            return
        where = pos or self._free_spot()
        note = {"text": text, "x": snap(where.x()), "y": snap(where.y())}
        self._edit("add note", lambda model: model.annotations.append(note))

    def edit_annotation(self, index: int, text: str | None = None) -> None:
        """Change a note's text; an empty text deletes it."""
        if not 0 <= index < len(self.model.annotations):
            return
        if self.locked:
            self.refuse_edit()
            return
        if text is None:
            from PySide6.QtWidgets import QInputDialog
            text, ok = QInputDialog.getMultiLineText(
                self, "Note", "Text:", self.model.annotations[index]["text"])
            if not ok:
                return

        def change(model):
            if text.strip():
                model.annotations[index]["text"] = text
            else:
                del model.annotations[index]
        self._edit("edit note", change)

    def _on_note_moved(self, index: int, x: float, y: float) -> None:
        def move(model):
            model.annotations[index].update(x=x, y=y)
        self._edit("move note", move)

    # ── export ──────────────────────────────────────────────────

    def export_image(self, path) -> None:
        """The diagram as SVG, PDF, PNG or JPEG, by the file's extension."""
        from .export import export_scene
        export_scene(self._scene, path)

    def print_diagram(self) -> bool:
        from .export import print_scene
        return print_scene(self._scene, self)

    def select_all(self) -> None:
        for item in self._blocks.values():
            item.setSelected(True)

    # ── clipboard ───────────────────────────────────────────────

    def copy_selection(self) -> None:
        ids = {i.block_id for i in self._scene.selectedItems()
               if isinstance(i, BlockItem)}
        if not ids:
            return
        data = self.model.to_dict()
        payload = {
            "blocks": [b for b in data["blocks"] if b["id"] in ids],
            "connections": [
                c for c in data["connections"]
                if c["src"].split(".")[0] in ids and c["dst"].split(".")[0] in ids
            ],
        }
        QApplication.clipboard().setText(json.dumps(payload))
        self.status.emit(f"Copied {len(payload['blocks'])} block(s)")

    def paste(self) -> None:
        if self.locked:
            self.refuse_edit()
            return
        try:
            payload = json.loads(QApplication.clipboard().text())
        except (ValueError, TypeError):
            return
        if not isinstance(payload, dict) or "blocks" not in payload:
            return
        self.undo_stack.push(cmd.PasteBlocks(self, payload, GRID * 3, GRID * 3))

    # ── wiring ──────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        """
        Start a wire, or finish the one already in progress.

        Both gestures work: **drag** from one port to another, or **click**
        one port and then click the other. The click-click form is the one
        that used to be dead — a second click on a port restarted the wire
        instead of completing it, so nothing ever connected and every
        abandoned attempt left a dashed line on the canvas.
        """
        if event.button() == Qt.MiddleButton:
            # Middle-drag pans, as in Simulink — over a block or a wire too,
            # and without disturbing a wire that is half drawn.
            self._pan_from = event.position()
            self.viewport().setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        item = self._item_at(event.position().toPoint())
        if event.button() != Qt.LeftButton:
            super().mousePressEvent(event)
            return

        if isinstance(item, PortItem) and self.locked:
            self.refuse_edit()
            event.accept()
            return
        if isinstance(item, PortItem):
            if self._pending_port is not None and item is not self._pending_port:
                self._finish_wire(item)
                self._cancel_wire()
            else:
                self._start_wire(item)
            event.accept()
            return

        if self._pending_port is not None:
            # Clicking anywhere else abandons the wire, rather than leaving an
            # invisible half-connection armed until something else clears it.
            self._cancel_wire()
            self.status.emit("Wiring cancelled")

        # Rubber-band only from empty canvas: starting one on top of a block
        # would make blocks undraggable.
        self.setDragMode(QGraphicsView.RubberBandDrag if item is None
                         else QGraphicsView.NoDrag)
        super().mousePressEvent(event)

    def _start_wire(self, port: PortItem) -> None:
        # Never leave the previous rubber band behind: a second _start_wire
        # used to orphan it in the scene, one stray dashed line per attempt.
        self._cancel_wire()
        self._pending_port = port
        port.set_highlight(True)
        self._rubber_wire = self._scene.addPath(
            QPainterPath(), QPen(hover_colour(), 2.0, Qt.DashLine))
        self._rubber_wire.setZValue(5)
        kind = "input" if port.is_input else "output"
        self.status.emit(
            f"Wiring from {port.block_id}.{port.port} ({kind}) — "
            f"click an {'output' if port.is_input else 'input'} port, "
            f"drop it on empty canvas to add a block (Alt: keep it), "
            f"or press Esc")
        self._highlight_targets(port, True)

    def _highlight_targets(self, port: PortItem, on: bool) -> None:
        """Light up the ports this wire could legally reach."""
        for item in self._blocks.values():
            for (name, is_input), candidate in item.ports.items():
                if candidate is port:
                    continue
                legal = (is_input != port.is_input and
                         candidate.block_id != port.block_id)
                if legal and on and is_input:
                    ref = PortRef(candidate.block_id, name)
                    legal = self.model.connection_into(ref) is None
                if legal:
                    candidate.set_highlight(on)

    def mouseMoveEvent(self, event) -> None:
        self._last_mouse = event.position().toPoint()
        if self._pan_from is not None:
            delta = event.position() - self._pan_from
            self._pan_from = event.position()
            h, v = self.horizontalScrollBar(), self.verticalScrollBar()
            h.setValue(h.value() - round(delta.x()))
            v.setValue(v.value() - round(delta.y()))
            event.accept()
            return
        if self._rubber_wire is not None and self._pending_port is not None:
            path = QPainterPath(self._pending_port.scene_pos())
            path.lineTo(self.mapToScene(event.position().toPoint()))
            self._rubber_wire.setPath(path)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MiddleButton and self._pan_from is not None:
            self._pan_from = None
            self.viewport().unsetCursor()
            event.accept()
            return
        if self._pending_port is not None:
            target = self._item_at(event.position().toPoint())
            if isinstance(target, PortItem) and target is not self._pending_port:
                # A drag that landed on another port: connect and finish.
                self._finish_wire(target)
                self._cancel_wire()
            elif (target is None and not event.modifiers() & Qt.AltModifier
                    and self._dragged_away(event.position())):
                # A drag that ended on nothing: offer a block to wire to.
                self.open_quick_insert(event.position().toPoint(),
                                       wire_from=self._pending_port)
            # Releasing on the starting port, or on empty space with Alt
            # held, leaves the wire *armed* so the next click can complete
            # it. Cancelling here is what broke click-click wiring: the
            # press had started a wire and the release immediately threw it
            # away.
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _finish_wire(self, target: PortItem) -> None:
        start = self._pending_port
        if start.is_input == target.is_input:
            self.status.emit(
                f"Cannot connect two {'inputs' if start.is_input else 'outputs'}"
                f" — a wire runs from an output to an input.")
            return
        src, dst = (target, start) if start.is_input else (start, target)
        try:
            self.undo_stack.push(cmd.Connect(
                self, f"{src.block_id}.{src.port}",
                f"{dst.block_id}.{dst.port}"))
            self.status.emit(f"Connected {src.block_id}.{src.port} → "
                             f"{dst.block_id}.{dst.port}")
        except ModelError as exc:
            self.status.emit(str(exc))

    def _cancel_wire(self) -> None:
        if self._pending_port is not None:
            self._highlight_targets(self._pending_port, False)
            self._pending_port.set_highlight(False)
            self._pending_port = None
        if self._rubber_wire is not None:
            self._scene.removeItem(self._rubber_wire)
            self._rubber_wire = None

    # ── arranging ───────────────────────────────────────────────

    def selected_blocks(self) -> list:
        from .items import BlockItem

        return [i for i in self._scene.selectedItems()
                if isinstance(i, BlockItem)]

    def align_selection(self, axis: str) -> int:
        """
        Line the selected blocks up. ``axis`` is ``"x"`` or ``"y"``.

        Returns how many moved, so a caller can say nothing happened rather
        than silently doing nothing.
        """
        blocks = self.selected_blocks()
        if self.locked:
            self.refuse_edit()
            return 0
        if len(blocks) < 2:
            self.status.emit("Select two or more blocks to align them")
            return 0
        if axis == "x":
            target = sum(b.pos().x() for b in blocks) / len(blocks)
            moves = [(b.block_id, target, b.pos().y()) for b in blocks]
        else:
            target = sum(b.pos().y() for b in blocks) / len(blocks)
            moves = [(b.block_id, b.pos().x(), target) for b in blocks]
        self.undo_stack.push(cmd.MoveBlocks(self, moves))
        return len(moves)

    def distribute_selection(self, axis: str) -> int:
        """Space the selected blocks evenly along ``axis``."""
        blocks = self.selected_blocks()
        if self.locked:
            self.refuse_edit()
            return 0
        if len(blocks) < 3:
            self.status.emit("Select three or more blocks to distribute them")
            return 0
        key = (lambda b: b.pos().x()) if axis == "x" else (lambda b: b.pos().y())
        ordered = sorted(blocks, key=key)
        first, last = key(ordered[0]), key(ordered[-1])
        step = (last - first) / (len(ordered) - 1)
        moves = []
        for index, block in enumerate(ordered):
            value = first + index * step
            if axis == "x":
                moves.append((block.block_id, value, block.pos().y()))
            else:
                moves.append((block.block_id, block.pos().x(), value))
        self.undo_stack.push(cmd.MoveBlocks(self, moves))
        return len(moves)

    # ── parameters ──────────────────────────────────────────────

    def _edit_params(self, block_id: str) -> None:
        """
        Double-click: descend into a subsystem, open a Scope's window (its
        parameters are in the inspector), or edit parameters.
        """
        block = self.model.block(block_id)
        if block.type_name == "Subsystem":
            self.descend(block_id)
            return
        if block.type_name == "Scope":
            self.scope_requested.emit(self.block_path(block_id))
            return

        if self.locked:
            self.refuse_edit()
            return
        from .params import ParamDialog

        dialog = ParamDialog(block, self)
        if dialog.exec() and dialog.changes:
            self.undo_stack.push(cmd.SetParams(self, block_id, dialog.changes))

    # ── PID tuning ──────────────────────────────────────────────

    def make_tune_dialog(self, block_id: str):
        """
        Build the tuning dialog for a PID block, plant and all.

        The plant is not asked for: it is *read off the diagram* by opening the
        loop at the controller and linearising the rest (see
        :func:`~evans.sim.linearize.plant_seen_by`). When that cannot be
        done — no loop, several outputs, a subsystem view — the dialog is
        still built, carrying the reason, so the user is told what to fix
        instead of the button silently doing nothing.
        """
        from .tune_dialog import PIDTuneDialog

        block = self.model.block(block_id)
        plant, notes, error = None, [], ""
        if self.inside_subsystem:
            error = ("Tuning needs the whole loop, but this subsystem only "
                     "shows part of it. Go up to the level where the PID and "
                     "its plant are both visible.")
        else:
            try:
                from ...sim.workspace import resolve_model
                found = plant_seen_by(
                    resolve_model(self.model, self.evaluate), block_id)
                plant, notes = found.tf, found.notes
            except (LinearizationError, CompileError, ModelError,
                    ValueError) as exc:
                error = str(exc)
        return PIDTuneDialog(block, plant, error, notes, self)

    def tune_pid(self, block_id: str) -> bool:
        """Open the tuner for a PID; write accepted gains through undo."""
        if self.model.block(block_id).type_name != "PID":
            return False
        if self.locked:
            self.refuse_edit()
            return False
        dialog = self.make_tune_dialog(block_id)
        if dialog.exec() and dialog.changes:
            self.undo_stack.push(cmd.SetParams(self, block_id, dialog.changes))
            self.status.emit(f"Tuned {block_id}: "
                             + ", ".join(f"{k} = {v:.5g}"
                                         for k, v in dialog.changes.items()))
            return True
        return False

    # ── hierarchy ───────────────────────────────────────────────

    def descend(self, block_id: str) -> None:
        """
        Open a subsystem's contents, remembering the way back.

        Edits inside are written back into the parent's ``model`` parameter
        when you ascend, as one undoable step — so descending, editing and
        coming back up is a single entry in the undo history rather than a
        trail the user has to unwind one block at a time.
        """
        block = self.model.block(block_id)
        self._stack.append((self.model, block_id, self.undo_stack))
        inner = block.inner_model()
        inner.name = block.params.get("name", block_id)
        self.model = inner
        self.undo_stack = _LockableStack(self)
        self.rebuild()
        self.fit_all()
        self.path_changed.emit(self.breadcrumb())

    def ascend(self) -> None:
        """Go back up one level, saving whatever changed inside."""
        if not self._stack:
            return
        inner = self.model
        parent, block_id, parent_stack = self._stack.pop()
        self.model = parent
        self.undo_stack = parent_stack
        if not self.locked:
            self.undo_stack.push(
                cmd.SetParams(self, block_id, {"model": inner.to_dict()}))
        self.rebuild()
        self.fit_all()
        self.path_changed.emit(self.breadcrumb())

    def breadcrumb(self) -> list[str]:
        """Names from the top level down to what is on screen."""
        names = [parent.name for parent, _bid, _stack in self._stack]
        return names + [self.model.name]

    def block_path(self, block_id: str) -> str:
        """A block on screen, named from the top level: ``"Sub/Scope1"``."""
        return "/".join([bid for _parent, bid, _stack in self._stack]
                        + [block_id])

    @property
    def inside_subsystem(self) -> bool:
        return bool(self._stack)

    def root_model(self) -> SimModel:
        """
        The top-level model, with any open subsystem's edits folded in.

        Running or saving while inside a subsystem must use the whole model,
        not just the part on screen.
        """
        if not self._stack:
            return self.model
        inner = self.model
        for parent, block_id, _stack in reversed(self._stack):
            parent.block(block_id).set_param("model", inner.to_dict())
            inner = parent
        return inner

    # ── input ───────────────────────────────────────────────────

    def keyPressEvent(self, event) -> None:
        key = event.key()
        if key == Qt.Key_Escape:
            if self._pending_port is not None:
                self._cancel_wire()
                self.status.emit("")
            elif self.inside_subsystem:
                self.ascend()
        elif key in (Qt.Key_Delete, Qt.Key_Backspace):
            self.delete_selection()
        elif event.matches(QKeySequence.Copy):
            self.copy_selection()
        elif event.matches(QKeySequence.Paste):
            self.paste()
        elif event.matches(QKeySequence.SelectAll):
            self.select_all()
        elif self._starts_quick_insert(event):
            self.open_quick_insert(self._typing_point(), text=event.text())
        else:
            super().keyPressEvent(event)
            return
        event.accept()

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(factor, factor)
            event.accept()
        else:
            super().wheelEvent(event)

    def _item_at(self, pos):
        """
        The topmost real item under a view point: a port, block or wire.

        Not ``itemAt``: while a wire is being drawn, its dashed preview ends
        under the cursor and sits above everything, so ``itemAt`` answered
        with the preview, never the input port being clicked. The click was
        taken as one on empty canvas, the wire was dropped and the block
        behind the port got selected instead: no wire could be made by
        clicking or dragging. The alignment guides are skipped the same way.
        """
        skip = {self._rubber_wire, *self._guides}
        for item in self.items(pos):
            if item not in skip:
                return item
        return None

    # ── quick insert ────────────────────────────────────────────
    #
    # A popup that picks a block type, opened three ways: double-click on
    # empty canvas, typing a letter, or a wire dropped on empty canvas. The
    # placement is deliberately local and simple (the point given, or for a
    # dropped wire the matching port on the drop point) so that a layout
    # pass can replace it later.

    @property
    def quick_insert(self):
        """The popup, built on first use."""
        if self._quick is None:
            from .quick_insert import QuickInsert
            self._quick = QuickInsert(self.viewport())
            self._quick.chosen.connect(self._quick_chosen)
            self._quick.cancelled.connect(self._quick_cancelled)
        return self._quick

    def open_quick_insert(self, view_pos: QPoint, text: str = "",
                          wire_from: PortItem | None = None) -> None:
        """
        Open the popup with its corner at ``view_pos`` (viewport pixels),
        ``text`` already typed. Whatever is chosen goes at that point; with
        ``wire_from`` (a wire in progress) only types with a port of the
        needed direction are listed, and the choice is wired to it.
        """
        if self.locked:
            self.refuse_edit()
            return
        point = QPoint(view_pos)
        self._quick_scene_pos = self.mapToScene(point)
        if wire_from is not None:
            self._quick_wire = (wire_from.block_id, wire_from.port,
                                wire_from.is_input)
            if self._rubber_wire is not None:
                path = QPainterPath(wire_from.scene_pos())
                path.lineTo(self._quick_scene_pos)
                self._rubber_wire.setPath(path)
            need = "output" if wire_from.is_input else "input"
        else:
            self._quick_wire = None
            need = None
        self.quick_insert.open_at(point, text, need)

    def _quick_chosen(self, type_name: str) -> None:
        wire, self._quick_wire = self._quick_wire, None
        if wire is None:
            self.add_block(type_name, self._quick_scene_pos)
        else:
            self._add_connected(type_name, wire, self._quick_scene_pos)
        self.setFocus()

    def _quick_cancelled(self) -> None:
        if self._quick_wire is not None:
            self._quick_wire = None
            self._cancel_wire()
            self.status.emit("Wiring cancelled")
        self.setFocus()

    def _add_connected(self, type_name: str, wire: tuple[str, str, bool],
                       drop: QPointF) -> None:
        """
        Add ``type_name`` with its first port of the right direction on
        ``drop``, wired to the port ``wire`` started from: one undo step.
        """
        block_id, port, is_input = wire
        if is_input and self.model.connection_into(
                PortRef(block_id, port)) is not None:
            self._cancel_wire()
            self.status.emit(f"{block_id}.{port} already has a wire")
            return
        want_input = not is_input
        probe = create(type_name, "_probe")
        first = (probe.inputs if want_input else probe.outputs)[0]
        shape = BlockItem(probe, 0.0, 0.0)      # kept alive: it owns its ports
        offset = shape.ports[(first, want_input)].pos()
        x, y = snap(drop.x() - offset.x()), snap(drop.y() - offset.y())
        self.undo_stack.beginMacro("Add connected block")
        try:
            add = cmd.AddBlock(self, type_name, x, y)
            self.undo_stack.push(add)
            new = f"{add.block_id}.{first}"
            old = f"{block_id}.{port}"
            self.undo_stack.push(cmd.Connect(
                self, *((new, old) if is_input else (old, new))))
            self.status.emit(f"Added {add.block_id} and connected it to "
                             f"{block_id}.{port}")
        except ModelError as exc:
            self.status.emit(str(exc))
        finally:
            self.undo_stack.endMacro()
        self._cancel_wire()

    def _dragged_away(self, pos: QPointF) -> bool:
        """Whether ``pos`` is far enough from the wire's port to be a drop."""
        start = QPointF(self.mapFromScene(self._pending_port.scene_pos()))
        return QLineF(start, pos).length() >= DROP_DISTANCE

    def _typing_point(self) -> QPoint:
        """Where typing opens the popup: the mouse, or else the view's centre."""
        rect = self.viewport().rect()
        if self._last_mouse is not None and rect.contains(self._last_mouse):
            return QPoint(self._last_mouse)
        return rect.center()

    def _starts_quick_insert(self, event) -> bool:
        """A plain printable character, with no wire or text edit in progress."""
        if self._pending_port is not None:
            return False
        if event.modifiers() & (Qt.ControlModifier | Qt.AltModifier
                                | Qt.MetaModifier):
            return False
        text = event.text()
        if len(text) != 1 or not text.isprintable() or text.isspace():
            return False
        focus = self._scene.focusItem()
        return not (focus is not None
                    and focus.flags() & QGraphicsItem.ItemAcceptsInputMethod)

    def mouseDoubleClickEvent(self, event) -> None:
        """On empty canvas: the quick insert. A block handles its own."""
        if (event.button() == Qt.LeftButton
                and self._item_at(event.position().toPoint()) is None):
            self.open_quick_insert(event.position().toPoint())
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def leaveEvent(self, event) -> None:
        self._last_mouse = None
        super().leaveEvent(event)

    def contextMenuEvent(self, event) -> None:
        self.context_menu(event.pos()).exec(event.globalPos())

    def context_menu(self, pos) -> QMenu:
        """The right-click menu for a view point, built but not shown."""
        menu = QMenu(self)
        item = self._item_at(pos)
        if isinstance(item, PortItem):
            item = item.parentItem()
        # Right-click acts on what is under the cursor, as everywhere else:
        # select it first, so "Delete" deletes it and not whatever happened
        # to be selected before (often nothing, so Delete did nothing).
        if isinstance(item, (BlockItem, WireItem)) and not item.isSelected():
            self._scene.clearSelection()
            item.setSelected(True)
        if isinstance(item, BlockItem):
            if item.block.type_name == "Subsystem":
                menu.addAction("Open subsystem",
                               lambda: self.descend(item.block_id))
                menu.addAction("Expand subsystem",
                               lambda: self.ungroup_subsystem(item.block_id))
            else:
                menu.addAction("Parameters…",
                               lambda: self._edit_params(item.block_id))
            if item.block.type_name == "PID":
                menu.addAction("Tune…", lambda: self.tune_pid(item.block_id))
            menu.addAction("Rotate 90°", self.rotate_selection)
            menu.addAction("Flip", self.flip_selection)
            menu.addAction("Create subsystem from selection",
                           lambda: self.create_subsystem())
            menu.addSeparator()
        elif isinstance(item, WireItem):
            conn = item.connection
            menu.addAction("Name signal…", lambda: self.name_signal(conn))
            if str(conn) in self.model.bends:
                menu.addAction("Reset wire route",
                               lambda: self.straighten(conn))
            menu.addSeparator()
        elif isinstance(item, AnnotationItem):
            index = item.index
            menu.addAction("Edit note…", lambda: self.edit_annotation(index))
            menu.addSeparator()
        else:
            scene_pos = self.mapToScene(pos)
            menu.addAction("Add note here…",
                           lambda: self.add_annotation(scene_pos))
            menu.addSeparator()
        if self.inside_subsystem:
            menu.addAction("↑ Up one level", self.ascend)
            menu.addSeparator()
        selected = self._scene.selectedItems()
        label = ("Delete wire" if len(selected) == 1
                 and isinstance(selected[0], WireItem)
                 else "Delete block" if len(selected) == 1 else "Delete")
        delete = menu.addAction(label, self.delete_selection)
        delete.setShortcut("Del")
        delete.setEnabled(bool(selected))
        menu.addAction("Copy", self.copy_selection)
        menu.addAction("Paste", self.paste)
        menu.addSeparator()
        menu.addAction("Fit to view", self.fit_all)
        menu.addAction("Export diagram…", self._ask_export)
        menu.addAction("Print diagram…", self.print_diagram)
        return menu

    def _ask_export(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Export diagram", f"{self.root_model().name}.svg",
            "SVG (*.svg);;PDF (*.pdf);;PNG (*.png)")
        if path:
            self.export_image(path)
            self.status.emit(f"Exported the diagram to {path}")

    # ── drag & drop from the palette ────────────────────────────

    @staticmethod
    def _dropped_files(mime) -> list:
        """Local files in a drop: they belong to the window, not the canvas."""
        if not mime.hasUrls():
            return []
        return [Path(url.toLocalFile()) for url in mime.urls()
                if url.isLocalFile()]

    def dragEnterEvent(self, event) -> None:
        if (event.mimeData().hasFormat(MIME_TYPE)
                or self._dropped_files(event.mimeData())):
            event.acceptProposedAction()

    def dragMoveEvent(self, event) -> None:
        if (event.mimeData().hasFormat(MIME_TYPE)
                or self._dropped_files(event.mimeData())):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        if not event.mimeData().hasFormat(MIME_TYPE):
            files = self._dropped_files(event.mimeData())
            if files:
                event.acceptProposedAction()
                self.files_dropped.emit(files)
            return
        type_name = bytes(event.mimeData().data(MIME_TYPE)).decode()
        if type_name in block_types():
            self.add_block(type_name,
                           self.mapToScene(event.position().toPoint()))
            event.acceptProposedAction()

    # ── view helpers ────────────────────────────────────────────

    def fit_all(self) -> None:
        rect = self._scene.itemsBoundingRect()
        if rect.isEmpty():
            self.resetTransform()
            return
        self.resetTransform()
        self.fitInView(rect.adjusted(-40, -40, 40, 40), Qt.KeepAspectRatio)
        # Never zoom past 1:1 — a three-block model filling the screen at 400%
        # looks broken rather than helpful.
        if self.transform().m11() > 1.0:
            self.resetTransform()
            self.centerOn(rect.center())

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        """Ground, with a dot at every fifth grid line in the ``rule`` colour."""
        t = theme.tokens()
        painter.fillRect(rect, QColor(t.ground))
        painter.setPen(QPen(QColor(t.rule), 3.0, Qt.SolidLine, Qt.SquareCap))
        step = GRID * 5
        x0 = int(rect.left() - rect.left() % step)
        y0 = int(rect.top() - rect.top() % step)
        y = y0
        while y < rect.bottom():
            x = x0
            while x < rect.right():
                painter.drawPoint(QPointF(x, y))
                x += step
            y += step

    def _on_selection(self) -> None:
        blocks = [i for i in self._scene.selectedItems()
                  if isinstance(i, BlockItem)]
        self.selection_changed.emit(blocks[0] if len(blocks) == 1 else None)
