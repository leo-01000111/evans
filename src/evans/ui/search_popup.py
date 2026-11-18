"""
The command palette: a field over a short list, in front of the window.

It is a child widget of the main window, not a top-level window, so showing
it steals no focus from the platform and cannot end up behind anything. The
caller (``MainWindow.show_search``) hands it the entries; matching and order
are :mod:`search`'s.

Looks follow the design system's plates: a 2 px frame, the hard 4 px offset
shadow, square corners, the selected row in the tab bars' black plate with
signal-yellow text. Keys: Up and Down move, Enter runs, Esc closes, typing
filters.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtCore import (
    QAbstractListModel,
    QEvent,
    QModelIndex,
    QObject,
    QRect,
    QSize,
    Qt,
)
from PySide6.QtGui import QColor, QFontMetrics, QPainter
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QLineEdit,
    QListView,
    QStyle,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QVBoxLayout,
    QWidget,
)

from . import search, theme
from .design import NORMAL, TIGHT
from .search import Entry

#: Spec: 560 px, or the window's width less 32 px when that is smaller.
WIDTH = 560
MARGIN = 32
#: The popup's top, under the top of the window.
TOP = 48
#: The design system's hard offset shadow.
SHADOW = 4
FRAME = 2
VISIBLE_ROWS = 10
PLACEHOLDER = "Search actions, blocks, commands, help"

_ENTRY_ROLE = Qt.UserRole + 1


class _Results(QAbstractListModel):
    """The entries on show; the entry itself rides on ``_ENTRY_ROLE``."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.entries: list[Entry] = []

    def set_entries(self, entries: Sequence[Entry]) -> None:
        self.beginResetModel()
        self.entries = list(entries)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:      # noqa: N802
        return 0 if parent.isValid() else len(self.entries)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self.entries):
            return None
        entry = self.entries[index.row()]
        if role == Qt.DisplayRole:
            return entry.title
        if role == Qt.AccessibleTextRole:
            parts = [entry.title, entry.section, entry.shortcut]
            return ", ".join(p for p in parts if p)
        if role == _ENTRY_ROLE:
            return entry
        return None


class _Row(QStyledItemDelegate):
    """Title left, its section muted after it, the shortcut right in mono."""

    def sizeHint(self, option, index) -> QSize:             # noqa: N802
        return QSize(option.rect.width(), row_height())

    def paint(self, painter: QPainter, option: QStyleOptionViewItem,
              index: QModelIndex) -> None:
        entry: Entry = index.data(_ENTRY_ROLE)
        t = theme.tokens()
        selected = bool(option.state & QStyle.State_Selected)
        rect: QRect = option.rect
        painter.save()
        if selected:
            painter.fillRect(rect, QColor(t.plate))
            ink = muted = QColor(t.on_plate)
        else:
            ink, muted = QColor(t.ink), QColor(t.ink_muted)
        inner = rect.adjusted(NORMAL, 0, -NORMAL, 0)

        right = inner.right()
        if entry.shortcut:
            mono = theme.data_font(9)
            painter.setFont(mono)
            painter.setPen(muted if not selected else ink)
            width = QFontMetrics(mono).horizontalAdvance(entry.shortcut)
            painter.drawText(QRect(right - width, rect.top(), width + 1,
                                   rect.height()),
                             Qt.AlignVCenter | Qt.AlignRight, entry.shortcut)
            right -= width + NORMAL

        title_font = theme.ui_font(10)
        painter.setFont(title_font)
        painter.setPen(ink)
        fm = QFontMetrics(title_font)
        available = max(0, right - inner.left())
        title = fm.elidedText(entry.title, Qt.ElideRight, available)
        painter.drawText(QRect(inner.left(), rect.top(), available,
                               rect.height()),
                         Qt.AlignVCenter | Qt.AlignLeft, title)
        used = fm.horizontalAdvance(title) + NORMAL
        room = available - used
        if entry.section and room > 24:
            small = theme.ui_font(8)
            painter.setFont(small)
            painter.setPen(muted)
            text = QFontMetrics(small).elidedText(
                entry.section, Qt.ElideRight, room)
            painter.drawText(QRect(inner.left() + used, rect.top(), room,
                                   rect.height()),
                             Qt.AlignVCenter | Qt.AlignLeft, text)
        painter.restore()


def row_height() -> int:
    return QFontMetrics(theme.ui_font(10)).height() + 2 * TIGHT + 2


class SearchPopup(QFrame):
    """The palette. ``MainWindow.show_search`` opens it."""

    def __init__(self, window: QWidget) -> None:
        super().__init__(window)
        self.setObjectName("SearchPopup")
        self.setAccessibleName("Command palette")
        self._window = window
        self._entries: list[Entry] = []
        self._current = None
        self._recent: list[str] = []
        self._previous_focus: QWidget | None = None
        self._ignore: list[QWidget] = []
        #: Called with the chosen entry, after the popup has closed.
        self.on_chosen: Callable[[Entry], None] = lambda entry: entry.run()

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, SHADOW, SHADOW)
        outer.setSpacing(0)
        self._plate = QFrame()
        self._plate.setObjectName("SearchPlate")
        outer.addWidget(self._plate)
        lay = QVBoxLayout(self._plate)
        lay.setContentsMargins(FRAME, FRAME, FRAME, FRAME)
        lay.setSpacing(0)

        self._field = QLineEdit()
        self._field.setObjectName("SearchField")
        self._field.setPlaceholderText(PLACEHOLDER)
        self._field.setAccessibleName("Search")
        self._field.setClearButtonEnabled(False)
        self._field.textChanged.connect(self._refresh)
        self._field.installEventFilter(self)
        lay.addWidget(self._field)

        self._model = _Results(self)
        self._list = QListView()
        self._list.setObjectName("SearchList")
        self._list.setAccessibleName("Results")
        self._list.setModel(self._model)
        self._list.setItemDelegate(_Row(self._list))
        self._list.setFocusPolicy(Qt.NoFocus)
        self._list.setFrameShape(QFrame.NoFrame)
        self._list.setEditTriggers(QListView.NoEditTriggers)
        self._list.setSelectionMode(QListView.SingleSelection)
        self._list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._list.setUniformItemSizes(True)
        self._list.clicked.connect(self._on_clicked)
        lay.addWidget(self._list)

        self._none = QLabel("No matches")
        self._none.setObjectName("SearchNone")
        self._none.setAccessibleName("No matches")
        self._none.setContentsMargins(NORMAL, TIGHT, NORMAL, TIGHT)
        lay.addWidget(self._none)

        self._restyle()
        theme.notifier().changed.connect(self._restyle)
        self.hide()

    # ── look ──

    def _restyle(self, *_ignored) -> None:
        t = theme.tokens()
        self._plate.setStyleSheet(
            f"QFrame#SearchPlate {{ background: {t.surface};"
            f" border: {FRAME}px solid {t.frame}; }}"
            f"QLineEdit#SearchField {{ background: {t.surface};"
            f" color: {t.ink}; border: none;"
            f" border-bottom: 1px solid {t.rule};"
            f" padding: {NORMAL}px; }}"
            f"QListView#SearchList {{ background: {t.surface};"
            f" color: {t.ink}; border: none; }}"
            f"QLabel#SearchNone {{ background: {t.surface};"
            f" color: {t.ink_muted}; }}")
        self._field.setFont(theme.ui_font(11))
        self.update()

    def paintEvent(self, event) -> None:                    # noqa: N802
        """The hard offset shadow: the plate's rectangle, moved 4 px."""
        plate = self._plate.geometry()
        p = QPainter(self)
        p.fillRect(plate.translated(SHADOW, SHADOW),
                   QColor(theme.tokens().shadow))
        p.end()

    # ── state ──

    @property
    def field(self) -> QLineEdit:
        return self._field

    @property
    def results(self) -> list[Entry]:
        return list(self._model.entries)

    @property
    def query(self) -> str:
        return self._field.text()

    @property
    def current_entry(self) -> Entry | None:
        index = self._list.currentIndex()
        if not index.isValid():
            return None
        return self._model.entries[index.row()]

    def ignore_clicks_on(self, widget: QWidget) -> None:
        """A press on ``widget`` does not close the popup (its own toggle)."""
        self._ignore.append(widget)

    # ── showing and hiding ──

    def open_with(self, entries: Sequence[Entry], current, recent: Sequence[str]
                  ) -> None:
        """Show the palette over ``entries``, ranked for ``current``."""
        self._entries = list(entries)
        self._current = current
        self._recent = list(recent)
        if not self.isVisible():
            self._previous_focus = QApplication.focusWidget()
        self._field.blockSignals(True)
        self._field.clear()
        self._field.blockSignals(False)
        self._refresh()
        self._place()
        self.show()
        self.raise_()
        self._field.setFocus(Qt.ShortcutFocusReason)
        QApplication.instance().installEventFilter(self)
        self._window.installEventFilter(self)

    def close_popup(self, restore_focus: bool = True) -> None:
        if not self.isVisible():
            return
        self.hide()
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        self._window.removeEventFilter(self)
        previous, self._previous_focus = self._previous_focus, None
        if restore_focus and previous is not None:
            try:
                if previous.isVisible():
                    previous.setFocus(Qt.OtherFocusReason)
            except RuntimeError:                  # the widget is gone
                pass

    def _place(self) -> None:
        window_width = self._window.width()
        plate = min(WIDTH, max(200, window_width - MARGIN))
        rows = min(max(len(self._model.entries), 0), VISIBLE_ROWS)
        self._list.setVisible(rows > 0)
        self._none.setVisible(rows == 0)
        self._list.setFixedHeight(rows * row_height())
        self._plate.setFixedWidth(plate)
        self._plate.adjustSize()
        self.setFixedWidth(plate + SHADOW)
        self.adjustSize()
        self.move((window_width - plate) // 2, TOP)

    # ── matching ──

    def _refresh(self, *_ignored) -> None:
        shown = search.rank(self._entries, self._field.text(), self._current,
                            self._recent)
        self._model.set_entries(shown)
        if shown:
            self._list.setCurrentIndex(self._model.index(0))
        self._place()

    def _move(self, step: int) -> None:
        count = self._model.rowCount()
        if not count:
            return
        row = (self._list.currentIndex().row() + step) % count \
            if self._list.currentIndex().isValid() else 0
        self._list.setCurrentIndex(self._model.index(row))
        self._list.scrollTo(self._model.index(row))

    def _on_clicked(self, index: QModelIndex) -> None:
        self._list.setCurrentIndex(index)
        self.choose()

    def choose(self) -> bool:
        """Close, then run the highlighted entry. False when there is none."""
        entry = self.current_entry
        if entry is None:
            return False
        self.close_popup()
        self.on_chosen(entry)
        return True

    # ── events ──

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:   # noqa: N802
        kind = event.type()
        if obj is self._field and kind == QEvent.KeyPress:
            key = event.key()
            if key == Qt.Key_Down:
                self._move(1)
            elif key == Qt.Key_Up:
                self._move(-1)
            elif key in (Qt.Key_PageDown, Qt.Key_PageUp):
                self._move(VISIBLE_ROWS if key == Qt.Key_PageDown
                           else -VISIBLE_ROWS)
            elif key in (Qt.Key_Return, Qt.Key_Enter):
                self.choose()
            elif key == Qt.Key_Escape:
                self.close_popup()
            else:
                return False
            return True
        if obj is self._window and kind == QEvent.Resize:
            self._place()
        elif kind == QEvent.MouseButtonPress and isinstance(obj, QWidget):
            if (obj is not self and not self.isAncestorOf(obj)
                    and not any(w is obj or w.isAncestorOf(obj)
                                for w in self._ignore)):
                self.close_popup()
        return False
