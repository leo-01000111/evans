"""
Help ▸ Keyboard shortcuts: every shortcut, from the same registry the command
palette searches, plus the few keys that belong to a widget and not to an
action. :func:`markdown` writes the same content for the documentation
(``help/pages/keyboard.md``); a test keeps the two from drifting apart.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from . import keys, theme
from .design import NORMAL, PANEL, SECTION, TIGHT
from .search import Entry

#: Keys no action owns: (where, key, what it does). Shown after the actions.
EXTRA_KEYS: tuple[tuple[str, str, str], ...] = (
    ("Anywhere", "Ctrl+`", "Go to the command window"),
    ("Model canvas", "Delete", "Delete the selected blocks and lines"),
    ("Model canvas", "Esc", "Leave the subsystem, or cancel what is in hand"),
    ("Model canvas", "Ctrl+wheel", "Zoom the diagram"),
    ("Command window", "Up / Down", "Walk through the commands typed before"),
    ("Command window", "Tab", "Complete the name being typed"),
    ("Command window", "Ctrl+Space", "Show every completion here"),
    ("Script editor", "F5", "Run the script, or continue when paused"),
    ("Script editor", "F10", "Run the paused line"),
    ("Script editor", "F11", "Step into the call on the paused line"),
)

_FIRST = ("File", "Edit", "View", "Help")


def groups(entries: list[Entry]) -> list[tuple[str, list[tuple[str, str]]]]:
    """``[(section, [(title, shortcut)])]`` for the entries that have one."""
    found: dict[str, list[tuple[str, str]]] = {}
    for entry in entries:
        if entry.shortcut:
            found.setdefault(entry.section, []).append(
                (entry.title, entry.shortcut))
    order = [s for s in _FIRST if s in found] + sorted(
        s for s in found if s not in _FIRST)
    return [(section, sorted(found[section], key=lambda p: p[0].lower()))
            for section in order]


def extra_groups() -> list[tuple[str, list[tuple[str, str]]]]:
    out: dict[str, list[tuple[str, str]]] = {}
    for where, key, what in EXTRA_KEYS:
        # On a Mac that key is Control, not Command (see `_build_menus`).
        shown = "⌃`" if keys.is_mac() and key == "Ctrl+`" else keys.label(key)
        out.setdefault(where, []).append((what, shown))
    return list(out.items())


def markdown(entries: list[Entry]) -> str:
    """The same sheet as a help page."""
    lines = ["# Keyboard shortcuts", "",
             "Every shortcut in the menus, and the few keys that belong to "
             "one widget. Press Ctrl+/ for this list in a window, and Ctrl+K "
             "or Ctrl+Shift+P to search every action by name. On a Mac, "
             "Ctrl is the Command key.", ""]
    for section, rows in [*groups(entries), *extra_groups()]:
        lines += [f"## {section}", ""]
        lines += [f"- {key}: {title}" for title, key in rows]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


class ShortcutsDialog(QDialog):
    """Non-modal, like Preferences; built by ``MainWindow.show_shortcuts``."""

    def __init__(self, entries: list[Entry], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Keyboard shortcuts")
        self.setObjectName("ShortcutsDialog")
        self.setAccessibleName("Keyboard shortcuts")
        self.setModal(False)
        self.resize(560, 560)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(PANEL, PANEL, PANEL, PANEL)
        outer.setSpacing(NORMAL)

        body = QWidget()
        grid = QGridLayout(body)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(SECTION)
        grid.setVerticalSpacing(TIGHT)
        grid.setColumnStretch(0, 1)
        row = 0
        self.rows: list[tuple[str, str, str]] = []
        for section, items in [*groups(entries), *extra_groups()]:
            heading = QLabel(section)
            heading.setFont(theme.label_font(8))
            heading.setAccessibleName(section)
            grid.addWidget(heading, row, 0, 1, 2)
            grid.setRowMinimumHeight(row, 0)
            row += 1
            for title, key in items:
                name = QLabel(title)
                name.setWordWrap(True)
                chord = QLabel(key)
                chord.setFont(theme.data_font(9))
                chord.setAccessibleName(f"{title}: {key}")
                chord.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                grid.addWidget(name, row, 0)
                grid.addWidget(chord, row, 1)
                self.rows.append((section, title, key))
                row += 1
            grid.setRowMinimumHeight(row, SECTION)
            row += 1
        grid.setRowStretch(row, 1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.NoFrame)
        scroll.setWidget(body)
        scroll.setAccessibleName("Shortcuts")
        outer.addWidget(scroll, stretch=1)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.close)
        outer.addWidget(buttons)
