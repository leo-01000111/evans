"""
The search field: the button that opens the command palette.

It sits in each workspace's own top strip (Analyse: the context bar; Model:
floating over the top of the canvas; Console: the tab row) where the palette
pops up anyway. It is a flat button dressed as a field, in the accent (the
signal yellow the tab bars use for selection), and big enough to be seen.
Clicking it asks the main window to toggle the palette
(`MainWindow.toggle_search`); typing happens in the palette's own field.
"""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QPushButton, QSizePolicy

from . import keys, theme

#: At most this wide, at least this tall (logical px).
MAX_WIDTH = 360
HEIGHT = 32


def chord_text() -> str:
    chord = keys.label("Ctrl+K")
    return chord if keys.is_mac() else chord.replace("+", " ")


class SearchField(QPushButton):
    """
    "Search   Ctrl K" in a yellow plate. Never what sets the window's minimum
    width: it just gets narrower.
    """

    def __init__(self, parent=None, max_width: int = MAX_WIDTH) -> None:
        super().__init__(f"Search   {chord_text()}", parent)
        self._max = max_width
        self.setObjectName("WorkspaceSearch")
        self.setAccessibleName("Search")
        self.setToolTip(keys.label(
            "Search actions, blocks, commands and help (Ctrl+K)"))
        self.setFocusPolicy(Qt.NoFocus)
        self.setCursor(Qt.IBeamCursor)
        self.setMaximumWidth(max_width)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(HEIGHT)
        # The global button font is the sign font at 9 pt; a field reads at
        # the palette's own size.
        self.setProperty("_hp_font", True)
        self.setFont(theme.ui_font(11))

    def sizeHint(self) -> QSize:                # noqa: N802 (Qt API)
        return QSize(self._max, HEIGHT)

    def minimumSizeHint(self) -> QSize:         # noqa: N802 (Qt API)
        return QSize(0, HEIGHT)
