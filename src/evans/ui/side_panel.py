"""
The side panel: one tabbed column at the right of each workspace.

Every workspace page is a horizontal splitter, ``[content | SidePanel]``.
The splitter belongs to the page, so a panel opened on Analyse cannot show
over Model, and the rail stays at the window's left edge; the docks this
replaced (the loop editor on the left, Cedric on the right) belonged to the
window and could end up either side of the rail.

Analyse has *Loop · Design · Cedric*, Model *Properties · Cedric*, Console
*Workspace · History · Cedric*. Cedric is always the last tab, and there is
one of him: the main window moves the same ``AssistantPanel`` into the
current workspace's ``cedric`` holder, so the conversation goes with you.

Each page sits in a frameless, widget-resizable ``QScrollArea``. Word-wrapped
text grows taller as it gets narrower, and without the scroll area a narrow
panel would push the window's minimum height up instead.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QTabBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from . import iconset, keys
from .design import TIGHT


class SidePanel(QWidget):
    """A tab bar over a stack of scrolled pages, with a close button."""

    #: Opened (True) or closed (False), by any route.
    toggled = Signal(bool)
    #: The key of the tab now showing.
    tab_changed = Signal(str)

    DEFAULT_WIDTH = 320
    MINIMUM_WIDTH = 240

    def __init__(self, name: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setObjectName(f"sidePanel{name.title()}" if name else "sidePanel")
        self.setAccessibleName(f"{name} side panel".strip().capitalize())
        self.setMinimumWidth(self.MINIMUM_WIDTH)
        self._keys: list[str] = []
        self._holders: dict[str, QWidget] = {}
        #: The width to come back at; the user's drag is kept on close.
        self._width = self.DEFAULT_WIDTH
        self._width_pending = True
        #: Open or closed, as asked. Not ``isHidden()``: a child widget
        #: counts as hidden until its window is first shown.
        self._open = True
        self._watched: QSplitter | None = None

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(TIGHT)
        # A bare QTabBar rather than a QTabWidget: the pages live in their
        # own stack so each can be scrolled, and the global style gives a
        # tab bar the sign font, like the Console's.
        self._bar = QTabBar()
        self._bar.setDocumentMode(True)
        self._bar.setExpanding(False)
        self._bar.setDrawBase(False)
        self._bar.setAccessibleName("Side panel tabs")
        self._bar.currentChanged.connect(self._on_bar_changed)
        header.addWidget(self._bar, stretch=1)

        self._close = QToolButton()
        self._close.setAutoRaise(True)
        self._close.setToolButtonStyle(Qt.ToolButtonIconOnly)
        iconset.bind(self._close, "close")
        self._close.setIconSize(iconset.size(16))
        self._close.setToolTip(keys.label("Close the side panel (Ctrl+\\)"))
        self._close.setAccessibleName("Close side panel")
        self._close.clicked.connect(lambda: self.set_open(False))
        header.addWidget(self._close, alignment=Qt.AlignTop)
        column.addLayout(header)

        self._stack = QStackedWidget()
        column.addWidget(self._stack, stretch=1)

    # ── tabs ────────────────────────────────────────────────────

    def add_tab(self, key: str, title: str,
                widget: QWidget | None = None) -> QWidget:
        """
        A page called ``title``, holding ``widget`` if given. Returns the
        page's container (also ``holder(key)``), whose layout a widget can
        be moved into later.
        """
        if key in self._holders:
            raise ValueError(f"the side panel already has a {key!r} tab")
        holder = QWidget()
        holder.setObjectName(f"sideHolder_{key}")
        layout = QVBoxLayout(holder)
        layout.setContentsMargins(TIGHT, TIGHT, TIGHT, TIGHT)
        layout.setSpacing(TIGHT)
        if widget is not None:
            layout.addWidget(widget)
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setWidget(holder)
        self._keys.append(key)
        self._holders[key] = holder
        self._stack.addWidget(scroll)
        index = self._bar.addTab(title)
        self._bar.setTabToolTip(index, title)
        return holder

    def holder(self, key: str) -> QWidget:
        """The container of tab ``key``; ``holder.layout().addWidget(w)``."""
        return self._holders[key]

    @property
    def keys(self) -> tuple[str, ...]:
        return tuple(self._keys)

    def title(self, key: str) -> str:
        return self._bar.tabText(self._keys.index(key))

    @property
    def current(self) -> str:
        index = self._bar.currentIndex()
        return self._keys[index] if 0 <= index < len(self._keys) else ""

    def set_current(self, key: str) -> None:
        """Show tab ``key``; an unknown key (an older build's) is ignored."""
        if key in self._keys:
            self._bar.setCurrentIndex(self._keys.index(key))

    def _on_bar_changed(self, index: int) -> None:
        if 0 <= index < len(self._keys):
            self._stack.setCurrentIndex(index)
            self.tab_changed.emit(self._keys[index])

    # ── open and closed ─────────────────────────────────────────

    @property
    def is_open(self) -> bool:
        """
        Whether the panel is open in its workspace. Not ``isVisible()``,
        which is also false while another workspace is in view.
        """
        return self._open

    def set_open(self, on: bool) -> None:
        on = bool(on)
        changed = on != self._open
        self._open = on
        self.setVisible(on)             # explicitly, even when unchanged
        if on and changed:
            self._width_pending = True
            self._apply_width()
        if changed:
            self.toggled.emit(on)

    # ── width ───────────────────────────────────────────────────
    #
    # The width is what was asked for (`set_preferred_width`, a restored
    # layout) or where the user last dragged the splitter handle; it is not
    # read back from the geometry, which lags behind until the next layout.

    @property
    def preferred_width(self) -> int:
        return self._width

    def set_preferred_width(self, width: int) -> None:
        self._width = max(int(width), self.MINIMUM_WIDTH)
        self._width_pending = True
        self._apply_width()

    def sizeHint(self) -> QSize:                    # noqa: N802 (Qt API)
        return QSize(self._width, super().sizeHint().height())

    def _splitter(self) -> QSplitter | None:
        parent = self.parentWidget()
        if not isinstance(parent, QSplitter):
            return None
        if parent is not self._watched:
            self._watched = parent
            parent.splitterMoved.connect(self._on_dragged)
        return parent

    def _on_dragged(self, *_ignored) -> None:
        """The user moved the handle: that is the width to come back at."""
        if self._open and self.isVisible() and self.width() > 0:
            self._width = max(self.width(), self.MINIMUM_WIDTH)

    def _apply_width(self) -> None:
        """Give the panel its width, taken from the content beside it."""
        splitter = self._splitter()
        if splitter is None or not self.is_open:
            return
        total = sum(splitter.sizes())
        index = splitter.indexOf(self)
        if total <= 0 or not splitter.isVisible():
            return                                   # on the next show
        sizes = splitter.sizes()
        width = min(self._width, max(total - self.MINIMUM_WIDTH,
                                     self.MINIMUM_WIDTH))
        others = [i for i in range(len(sizes)) if i != index and sizes[i] > 0]
        give = sizes[index] - width
        if others:
            # The width comes from (or goes back to) the widest neighbour.
            widest = max(others, key=lambda i: sizes[i])
            sizes[widest] = max(sizes[widest] + give, 0)
        sizes[index] = width
        splitter.setSizes(sizes)
        self._width_pending = False

    def showEvent(self, event) -> None:              # noqa: N802 (Qt API)
        super().showEvent(event)
        if self._width_pending:
            self._apply_width()


def page_with_panel(content: QWidget, panel: SidePanel) -> QSplitter:
    """``[content | panel]``: the content stretches, the panel keeps its width."""
    splitter = QSplitter(Qt.Horizontal)
    splitter.setObjectName("sidePanelSplitter")
    splitter.addWidget(content)
    splitter.addWidget(panel)
    splitter.setStretchFactor(0, 1)
    splitter.setStretchFactor(1, 0)
    splitter.setCollapsible(0, False)
    splitter.setCollapsible(1, False)
    return splitter
