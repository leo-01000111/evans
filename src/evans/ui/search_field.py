"""
The search field: one, centred in the window's title strip.

At rest it is a thin frame with "Search…" on the left and the shortcut on
the right in the mono face, about 55 % opaque and with no fill, so it sits
in the strip like part of it. Under the mouse, and while the palette is open,
it is at full strength with a 2 px signal-yellow frame. A click asks the
main window to toggle the palette (`MainWindow.toggle_search`); the palette
(:mod:`search_popup`) then grows out of this very rectangle.

It is a child of the main window rather than of the title bar, so the opened
palette can reach over the strip and the content below it. With the
integrated title bar its place is :meth:`TitleBar.search_rect`; without one
(macOS, Linux, or the preference off) it floats top-centre over the current
workspace's content instead.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from . import keys, theme
from .design import NORMAL, TIGHT

#: At most this wide; the strip gives it less when the menus need the room.
MAX_WIDTH = 360
#: Narrower than this and it is not worth showing.
MIN_WIDTH = 140
HEIGHT = 24
#: How much of itself it shows at rest.
REST_OPACITY = 0.55
PLACEHOLDER = "Search…"


def chord_text() -> str:
    return keys.label("Ctrl+K")


class SearchField(QWidget):
    """
    "Search…   Ctrl+K". Never what sets the window's minimum width: it is
    laid over the strip, not in it.
    """

    clicked = Signal()

    def __init__(self, window: QWidget) -> None:
        super().__init__(window)
        self._window = window
        self._open = False
        self.setObjectName("TitleSearch")
        self.setAccessibleName("Search")
        self.setAccessibleDescription(
            "Opens the command palette: actions, blocks, commands and help")
        self.setToolTip(keys.label(
            "Search actions, blocks, commands and help (Ctrl+K)"))
        self.setFocusPolicy(Qt.NoFocus)
        self.setCursor(Qt.IBeamCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setFixedHeight(HEIGHT)
        self.setMinimumWidth(0)
        window.installEventFilter(self)
        bar = getattr(window, "title_bar", None)
        if bar is not None:
            bar.installEventFilter(self)
            bar.geometry_changed.connect(self.place)
            bar.add_client_overlay(self)
        theme.notifier().changed.connect(lambda *_a: self.update())

    # ── what it says ──

    @property
    def placeholder(self) -> str:
        return PLACEHOLDER

    @property
    def chord(self) -> str:
        return chord_text()

    @property
    def is_open(self) -> bool:
        return self._open

    def set_open(self, on: bool) -> None:
        """Dressed as open (yellow frame) while the palette is out."""
        if on != self._open:
            self._open = on
            self.update()

    # ── where it is ──

    def rest_rect(self) -> QRect:
        """Its place, in the window's coordinates, at rest."""
        window = self._window
        bar = getattr(window, "title_bar", None)
        if bar is not None and window.integrated_title_bar:
            local = bar.search_rect()
            return QRect(bar.mapTo(window, local.topLeft()), local.size())
        stack = window.centralWidget()
        top = stack.mapTo(window, QPoint(0, 0)).y() if stack is not None \
            else 0
        width = max(0, min(MAX_WIDTH, window.width() - 2 * NORMAL))
        return QRect((window.width() - width) // 2, top + TIGHT, width,
                     HEIGHT)

    def anchor_rect(self) -> QRect:
        """What the palette grows out of (never narrower than MIN_WIDTH)."""
        rect = self.rest_rect()
        if rect.width() < MIN_WIDTH:
            rect = QRect(rect.x() + (rect.width() - MIN_WIDTH) // 2, rect.y(),
                         MIN_WIDTH, rect.height())
        return rect

    def place(self, *_ignored) -> None:
        """Put it where it belongs and bring it to the front."""
        try:
            rect = self.rest_rect()
        except RuntimeError:                  # the window is being destroyed
            return
        shown = rect.width() >= MIN_WIDTH
        self.setGeometry(rect)
        self.setVisible(shown)
        if shown:
            self.raise_()
            popup = getattr(self._window, "_search", None)
            if popup is not None and popup.isVisible():
                popup.raise_()

    def eventFilter(self, obj, event) -> bool:      # noqa: N802 (Qt API)
        kind = event.type()
        if obj is self._window and kind in (QEvent.Resize, QEvent.Show):
            self.place()
        elif obj is not self._window and kind in (
                QEvent.LayoutRequest, QEvent.Show):
            # The strip lays itself out after this; look again then.
            QTimer.singleShot(0, self.place)
        return False

    def sizeHint(self) -> QSize:                # noqa: N802 (Qt API)
        return QSize(MAX_WIDTH, HEIGHT)

    def minimumSizeHint(self) -> QSize:         # noqa: N802 (Qt API)
        return QSize(0, HEIGHT)

    # ── look ──

    def paintEvent(self, event) -> None:        # noqa: N802 (Qt API)
        t = theme.tokens()
        hot = self.underMouse() or self._open
        p = QPainter(self)
        p.setOpacity(1.0 if hot else REST_OPACITY)
        if hot:
            p.setPen(QPen(QColor(t.signal), 2))
            p.drawRect(self.rect().adjusted(1, 1, -1, -1))
        else:
            p.setPen(QPen(QColor(t.ink), 1))
            p.drawRect(self.rect().adjusted(0, 0, -1, -1))
        inner = self.rect().adjusted(NORMAL, 0, -NORMAL, 0)
        mono = theme.data_font(8.5)
        p.setFont(mono)
        p.setPen(QColor(t.ink_muted))
        chord = chord_text()
        chord_w = QFontMetrics(mono).horizontalAdvance(chord)
        show_chord = inner.width() > chord_w + 60
        if show_chord:
            p.drawText(QRect(inner.right() - chord_w, 0, chord_w + 1,
                             self.height()),
                       Qt.AlignVCenter | Qt.AlignRight, chord)
        font = theme.ui_font(10)
        p.setFont(font)
        room = inner.width() - ((chord_w + NORMAL) if show_chord else 0)
        text = QFontMetrics(font).elidedText(PLACEHOLDER, Qt.ElideRight,
                                             max(0, room))
        p.drawText(QRect(inner.left(), 0, max(0, room), self.height()),
                   Qt.AlignVCenter | Qt.AlignLeft, text)
        p.end()

    def enterEvent(self, event) -> None:        # noqa: N802 (Qt API)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:        # noqa: N802 (Qt API)
        self.update()
        super().leaveEvent(event)

    # ── clicks ──

    def mousePressEvent(self, event) -> None:   # noqa: N802 (Qt API)
        if event.button() == Qt.LeftButton:
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:  # noqa: N802 (Qt API)
        if (event.button() == Qt.LeftButton
                and self.rect().contains(event.position().toPoint())):
            event.accept()
            self.clicked.emit()
            return
        super().mouseReleaseEvent(event)
