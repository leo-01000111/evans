"""
Preferences: the settings that outlast a session, on one page.

They used to be spread over four menus: Settings (one item), View (theme, the
classic block boxes, the integrated title bar), File (autosave) and Help
(update checks). Here each is one control, bound to the function that already
did the work, and takes effect at once: there is no OK and no Cancel, only
*Close*.

The dialog is not modal. ``MainWindow.show_preferences`` shows it;
:func:`preferences_dialog` builds it without showing it, which is how the tests
drive it.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QVBoxLayout,
    QWidget,
)

from . import persist, recovery, theme, winframe
from .design import NORMAL, PANEL, SectionCard
from .sim import shapes

_THEMES = (
    (theme.Mode.SYSTEM, "System", "Follow the operating system"),
    (theme.Mode.DAY, "Day", "Dry concrete: light ground, black ink"),
    (theme.Mode.NIGHT, "Night", "Asphalt: dark ground, pale ink"),
)


def _interval_label(seconds: int) -> str:
    return f"Every {seconds} s" if seconds < 60 else f"Every {seconds // 60} min"


#: Whether *On launch* is offered. False until the Start page exists (R8).
SHOW_STARTUP_CHOICE = False


class PreferencesDialog(QDialog):
    """One page, three groups: General, Appearance, Model."""

    def __init__(self, window, parent=None) -> None:
        super().__init__(parent or window)
        self._window = window
        self.setWindowTitle("Preferences")
        self.setObjectName("Preferences")
        self.setModal(False)
        self.setAccessibleName("Preferences")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(PANEL, PANEL, PANEL, PANEL)
        outer.setSpacing(NORMAL)

        # ── General ──
        general = self._group(outer, "General")
        self.startup = QComboBox()
        self.startup.addItem("Start page", "start")
        self.startup.addItem("Reopen what was open", "reopen")
        self.startup.setToolTip(
            "What Evans shows when it opens (the Start page arrives with the "
            "projects)")
        self._add(general, "On launch", self.startup, "On launch")
        # Nothing reads startup/show until the Start page (Phase 8 R8):
        # keep the control and its key, but do not offer a choice that does
        # nothing. R8 shows the row again.
        general.setRowVisible(self.startup, SHOW_STARTUP_CHOICE)
        self.autosave = QCheckBox("Keep copies of unsaved work")
        self.autosave.setToolTip(
            "Keep a copy of unsaved scripts, the live script and the model, "
            "to offer back if Evans closes without being asked to")
        self._add(general, "Autosave for crash recovery", self.autosave,
                  "Autosave for crash recovery")
        self.autosave_interval = QComboBox()
        for seconds in recovery.INTERVALS:
            self.autosave_interval.addItem(_interval_label(seconds), seconds)
        self._add(general, "Autosave interval", self.autosave_interval,
                  "Autosave interval")
        self.auto_update = QCheckBox("Check once a day, a few seconds "
                                     "after launch")
        self._add(general, "Check for updates automatically",
                  self.auto_update, "Check for updates automatically")

        # ── Appearance ──
        appearance = self._group(outer, "Appearance")
        self.theme = QComboBox()
        for mode, name, tip in _THEMES:
            self.theme.addItem(name, mode.value)
            self.theme.setItemData(self.theme.count() - 1, tip,
                                   Qt.ToolTipRole)
        self.theme.setToolTip("Changing the theme restarts Evans")
        self._add(appearance, "Theme", self.theme, "Theme")
        self.title_bar = QCheckBox("Menus and window buttons in one strip")
        self.title_bar.setToolTip(
            "Windows only; this system draws its own title bar"
            if not winframe.supported() else
            "Menus and window buttons in one strip (Windows)")
        self.title_bar.setEnabled(winframe.supported())
        self._add(appearance, "Integrated title bar", self.title_bar,
                  "Integrated title bar")
        self.classic_boxes = QCheckBox("Draw every block as a plain rectangle")
        self._add(appearance, "Classic block boxes", self.classic_boxes,
                  "Classic block boxes")
        self.snapshot_bar = QCheckBox("Show the Snapshot, Restore and "
                                      "Compare row")
        self._add(appearance, "Snapshot bar", self.snapshot_bar,
                  "Snapshot bar")

        # ── Model ──
        model = self._group(outer, "Model")
        self.scope_in = QComboBox()
        self.scope_in.addItem("Its own window", "window")
        self.scope_in.addItem("The side panel", "panel")
        self.scope_in.setToolTip(
            "Where a double-click on a Scope block opens it")
        self._add(model, "Scope opens in", self.scope_in, "Scope opens in")

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.close)
        buttons.button(QDialogButtonBox.Close).setAccessibleName("Close")
        outer.addWidget(buttons)

        self.sync()
        self.startup.currentIndexChanged.connect(self._on_startup)
        self.autosave.toggled.connect(self._on_autosave)
        self.autosave_interval.currentIndexChanged.connect(self._on_autosave)
        self.auto_update.toggled.connect(persist.set_update_auto_check)
        self.theme.currentIndexChanged.connect(self._on_theme)
        self.title_bar.toggled.connect(self._on_title_bar)
        self.classic_boxes.toggled.connect(shapes.set_classic)
        self.snapshot_bar.toggled.connect(window.set_snapshot_bar_visible)
        self.scope_in.currentIndexChanged.connect(self._on_scope)

    # ── building ────────────────────────────────────────────────

    @staticmethod
    def _group(outer: QVBoxLayout, title: str) -> QFormLayout:
        card = SectionCard(title)
        form = QFormLayout()
        form.setSpacing(NORMAL)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        card.body.addLayout(form)
        outer.addWidget(card)
        return form

    @staticmethod
    def _add(form: QFormLayout, label: str, widget: QWidget,
             name: str) -> None:
        widget.setAccessibleName(name)
        form.addRow(label, widget)

    # ── the controls follow the settings ─────────────────────────

    def sync(self) -> None:
        """Show the settings as they are now, without applying anything."""
        window = self._window
        for widget, value in (
            (self.startup, persist.startup_show()),
            (self.autosave_interval, window._autosave_interval),
            (self.theme, theme.mode().value),
            (self.scope_in, persist.scope_opens_in()),
        ):
            widget.blockSignals(True)
            widget.setCurrentIndex(max(widget.findData(value), 0))
            widget.blockSignals(False)
        for widget, value in (
            (self.autosave, window._autosave_enabled),
            (self.auto_update, persist.update_auto_check()),
            (self.title_bar,
             persist.integrated_title_bar(default=winframe.supported())),
            (self.classic_boxes, shapes.classic()),
            (self.snapshot_bar, persist.snapshot_bar()),
        ):
            widget.blockSignals(True)
            widget.setChecked(bool(value))
            widget.blockSignals(False)
        self.autosave_interval.setEnabled(self.autosave.isChecked())

    # ── the controls act ────────────────────────────────────────

    def _on_startup(self, *_ignored) -> None:
        persist.set_startup_show(self.startup.currentData())

    def _on_autosave(self, *_ignored) -> None:
        self._window.set_autosave(self.autosave.isChecked(),
                                  self.autosave_interval.currentData())
        self.autosave_interval.setEnabled(self.autosave.isChecked())

    def _on_theme(self, *_ignored) -> None:
        """Asks to restart; if it is declined the old choice stays shown."""
        self._window.choose_theme(theme.Mode(self.theme.currentData()))
        self.sync()

    def _on_title_bar(self, on: bool) -> None:
        self._window.set_integrated_title_bar(on)
        self.sync()                        # it falls back where Windows refuses

    def _on_scope(self, *_ignored) -> None:
        persist.set_scope_opens_in(self.scope_in.currentData())


def preferences_dialog(window) -> PreferencesDialog:
    """The Preferences dialog, built and not shown. Tests drive its controls."""
    return PreferencesDialog(window)
