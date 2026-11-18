"""
Quick insert: a small field over a short list of block types, on the canvas.

Double-click on empty canvas, start typing with the canvas focused, or drop a
wire on empty canvas, and this opens where you are. Type a few letters of a
block's name, Up and Down to move, Enter to insert, Esc (or a click elsewhere)
to close. Matching is :func:`evans.ui.search.score`, the command palette's.

The popup only chooses a type; where the block goes, and the wire, are the
canvas's business (``SimCanvas.open_quick_insert``).
"""

from __future__ import annotations

from functools import lru_cache

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...sim.block import by_category, create
from .. import theme
from ..design import NORMAL, TIGHT
from ..search import score

#: Spec: 220 px wide, at most eight block types.
WIDTH = 220
ROWS = 8
SHADOW = 4
FRAME = 2

#: Shown, in this order, before anything is typed.
COMMON = ("Step", "Gain", "Sum", "Integrator", "TransferFcn", "Scope",
          "Constant", "Saturation", "Sine", "Derivative")

_TYPE_ROLE = Qt.UserRole + 1


@lru_cache(maxsize=1)
def catalog() -> tuple[tuple[str, str, str, bool, bool], ...]:
    """
    Every block type the palette offers: ``(name, category, description,
    has_input, has_output)``. The ports are those of a block made with its
    default parameters, which is the block that gets inserted.
    """
    out = []
    for category, classes in by_category().items():
        for cls in classes:
            try:
                block = create(cls.type_name, "_probe")
                has_in, has_out = bool(block.inputs), bool(block.outputs)
            except Exception:                                # noqa: BLE001
                continue            # a type that cannot be made bare is not offered
            out.append((cls.type_name, category, cls.description,
                        has_in, has_out))
    return tuple(out)


def rank(query: str, need: str | None = None, limit: int = ROWS) -> list[str]:
    """
    The block types that fit ``query``, best first, at most ``limit``.

    ``need`` is ``"input"`` or ``"output"`` to list only types with a port of
    that direction (a wire dropped on empty canvas), or None for all of them.
    """
    pool = [row for row in catalog()
            if need is None
            or (need == "input" and row[3])
            or (need == "output" and row[4])]
    if not query.strip():
        order = {name: i for i, name in enumerate(COMMON)}
        pool.sort(key=lambda row: (order.get(row[0], len(order)), row[0]))
        return [row[0] for row in pool[:limit]]
    scored = []
    for name, category, _description, _i, _o in pool:
        value = score(query, name)
        if value is None:
            value = score(query, f"{category} {name}")
            if value is None:
                continue
            value -= 20.0           # a category match ranks under a name match
        scored.append((-value, name))
    scored.sort()
    return [name for _value, name in scored[:limit]]


class _Field(QLineEdit):
    """A line edit that hands Up, Down, Enter and Esc to the popup."""

    move = Signal(int)
    accepted_key = Signal()
    cancelled_key = Signal()

    def keyPressEvent(self, event) -> None:                  # noqa: N802
        key = event.key()
        if key == Qt.Key_Down:
            self.move.emit(1)
        elif key == Qt.Key_Up:
            self.move.emit(-1)
        elif key in (Qt.Key_Return, Qt.Key_Enter):
            self.accepted_key.emit()
        elif key == Qt.Key_Escape:
            self.cancelled_key.emit()
        else:
            super().keyPressEvent(event)
            return
        event.accept()


class QuickInsert(QFrame):
    """The popup. A child of the canvas viewport."""

    #: A type was chosen (Enter, or a click on its row).
    chosen = Signal(str)
    #: Closed without a choice (Esc, or a click elsewhere).
    cancelled = Signal()

    def __init__(self, viewport: QWidget) -> None:
        super().__init__(viewport)
        self.setObjectName("QuickInsert")
        self.setAccessibleName("Quick insert")
        self.setAccessibleDescription("Type a block name, Enter to insert")
        self._need: str | None = None
        self._types: list[str] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, SHADOW, SHADOW)
        outer.setSpacing(0)
        self._plate = QFrame()
        self._plate.setObjectName("QuickInsertPlate")
        outer.addWidget(self._plate)
        lay = QVBoxLayout(self._plate)
        lay.setContentsMargins(FRAME, FRAME, FRAME, FRAME)
        lay.setSpacing(0)

        self._field = _Field()
        self._field.setObjectName("QuickInsertField")
        self._field.setPlaceholderText("Add a block")
        self._field.setAccessibleName("Block to insert")
        self._field.textChanged.connect(self._refresh)
        self._field.move.connect(self._move)
        self._field.accepted_key.connect(self.choose)
        self._field.cancelled_key.connect(self.cancel)
        lay.addWidget(self._field)

        self._list = QListWidget()
        self._list.setObjectName("QuickInsertList")
        self._list.setAccessibleName("Matching blocks")
        self._list.setFocusPolicy(Qt.NoFocus)
        self._list.setFrameShape(QFrame.NoFrame)
        self._list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._list.itemClicked.connect(self._on_clicked)
        lay.addWidget(self._list)

        self._none = QLabel("No block fits")
        self._none.setObjectName("QuickInsertNone")
        self._none.setAccessibleName("No block fits")
        self._none.setContentsMargins(NORMAL, TIGHT, NORMAL, TIGHT)
        lay.addWidget(self._none)

        self._plate.setFixedWidth(WIDTH)
        self.setFixedWidth(WIDTH + SHADOW)
        self._restyle()
        theme.notifier().changed.connect(self._restyle)
        self.hide()

    # ── look ──

    def _restyle(self, *_ignored) -> None:
        t = theme.tokens()
        self._plate.setStyleSheet(
            f"QFrame#QuickInsertPlate {{ background: {t.surface};"
            f" border: {FRAME}px solid {t.frame}; }}"
            f"QLineEdit#QuickInsertField {{ background: {t.surface};"
            f" color: {t.ink}; border: none;"
            f" border-bottom: 1px solid {t.rule}; padding: {TIGHT}px; }}"
            f"QListWidget#QuickInsertList {{ background: {t.surface};"
            f" color: {t.ink}; border: none; outline: none; }}"
            f"QListWidget#QuickInsertList::item {{ padding: {TIGHT}px; }}"
            f"QListWidget#QuickInsertList::item:selected {{"
            f" background: {t.plate}; color: {t.on_plate}; }}"
            f"QLabel#QuickInsertNone {{ background: {t.surface};"
            f" color: {t.ink_muted}; }}")
        self._field.setFont(theme.ui_font(10))
        self._list.setFont(theme.ui_font(10))
        self.update()

    def paintEvent(self, event) -> None:                     # noqa: N802
        """The design system's hard offset shadow."""
        plate = self._plate.geometry()
        painter = QPainter(self)
        painter.fillRect(plate.translated(SHADOW, SHADOW),
                         QColor(theme.tokens().shadow))
        painter.end()

    # ── state ──

    @property
    def field(self) -> QLineEdit:
        return self._field

    @property
    def results(self) -> list[str]:
        """The type names on show, best first."""
        return list(self._types)

    @property
    def current_type(self) -> str | None:
        item = self._list.currentItem()
        return item.data(_TYPE_ROLE) if item is not None else None

    # ── showing and hiding ──

    def open_at(self, point: QPoint, text: str = "",
                need: str | None = None) -> None:
        """
        Show the popup with its top-left at ``point`` (viewport pixels, moved
        in if it would leave the view), the field holding ``text`` already.
        """
        self._need = need
        self._field.blockSignals(True)
        self._field.setText(text)
        self._field.blockSignals(False)
        self._refresh()
        self._place(point)
        self.show()
        self.raise_()
        self._field.setFocus(Qt.ShortcutFocusReason)
        self._field.setCursorPosition(len(text))
        QApplication.instance().installEventFilter(self)

    def _close(self) -> bool:
        if not self.isVisible():
            return False
        self.hide()
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        return True

    def cancel(self) -> None:
        if self._close():
            self.cancelled.emit()

    def choose(self) -> bool:
        """Close and report the highlighted type. False when none fits."""
        name = self.current_type
        if name is None:
            return False
        self._close()
        self.chosen.emit(name)
        return True

    def _place(self, point: QPoint) -> None:
        rows = len(self._types)
        self._list.setVisible(rows > 0)
        self._none.setVisible(rows == 0)
        if rows:
            height = self._list.sizeHintForRow(0)
            self._list.setFixedHeight(max(height, 1) * rows)
        self._plate.adjustSize()
        self.adjustSize()
        parent = self.parentWidget()
        x, y = point.x(), point.y()
        if parent is not None:
            area: QRect = parent.rect()
            x = max(0, min(x, area.width() - self.width()))
            y = max(0, min(y, area.height() - self.height()))
        self.move(x, y)

    # ── matching ──

    def _refresh(self, *_ignored) -> None:
        self._types = rank(self._field.text(), self._need)
        descriptions = {row[0]: (row[1], row[2]) for row in catalog()}
        self._list.clear()
        for name in self._types:
            category, description = descriptions[name]
            item = QListWidgetItem(name)
            item.setData(_TYPE_ROLE, name)
            item.setToolTip(f"{category}: {description}" if description
                            else category)
            item.setData(Qt.AccessibleTextRole, f"{name}, {category}")
            self._list.addItem(item)
        if self._types:
            self._list.setCurrentRow(0)
        if self.isVisible():
            self._place(self.pos())

    def _move(self, step: int) -> None:
        count = self._list.count()
        if count:
            self._list.setCurrentRow((self._list.currentRow() + step) % count)

    def _on_clicked(self, item: QListWidgetItem) -> None:
        self._list.setCurrentItem(item)
        self.choose()

    # ── events ──

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:   # noqa: N802
        if event.type() == QEvent.MouseButtonPress and isinstance(obj, QWidget):
            if obj is not self and not self.isAncestorOf(obj):
                self.cancel()
        return False
