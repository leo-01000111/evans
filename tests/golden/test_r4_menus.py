"""
R4: four menus, Preferences, the per-workspace bottom bar, a slimmer context bar.

The window is shared (module scope) and put back by the `reset` fixture.
Nothing here opens a modal dialog: Preferences is built by
`preferences_dialog()` and its controls driven directly.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="Qt not available")

import control as ctl
import numpy as np
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMenu

from evans.core.architecture import CourseArchitecture
from evans.core.session import load_session_dict, session_dict
from evans.core.tf_utils import unity
from evans.ui import persist
from evans.ui.design import Status
from evans.ui.guard import ErrorBanner
from evans.ui.mainwindow import MainWindow
from evans.ui.preferences import PreferencesDialog, preferences_dialog
from evans.ui.workspace import Workspace

TARGET_W, TARGET_H = 1280, 720


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def win(app):
    window = MainWindow(CourseArchitecture())
    window.show()
    _settle(app)
    yield window
    window.hide()


@pytest.fixture(autouse=True)
def reset(win, app):
    load_session_dict(win._arch, session_dict(CourseArchitecture()))
    win._loop_undo.clear()
    win._after_loop_change()
    win._reset_side_panels()
    win.show_workspace(Workspace.ANALYSE)
    win._grid.set_layout_size(1, ("step",))
    win.resize(1400, 850)
    for banner in win.findChildren(ErrorBanner):
        banner.clear()
    _settle(app)
    yield


def _settle(app, rounds: int = 15) -> None:
    for _ in range(rounds):
        app.processEvents()


def _menu(win, title: str) -> QMenu:
    # Found as children: a menu got through `QAction.menu()` of a temporary
    # wrapper can be gone by the time it is used.
    for menu in win.menuBar().findChildren(QMenu):
        if menu.title().replace("&", "") == title                 and menu.parent() is win.menuBar():
            return menu
    raise AssertionError(title)


def _submenu(menu: QMenu, title: str) -> QMenu:
    for sub in menu.findChildren(QMenu):
        if sub.title().replace("&", "") == title:
            return sub
    raise AssertionError(title)


def _texts(menu: QMenu) -> list[str]:
    return [a.text().replace("&", "") for a in menu.actions()
            if not a.isSeparator()]


def _walk(menu: QMenu):
    subs = {sub.menuAction(): sub for sub in menu.findChildren(QMenu)}
    for action in menu.actions():
        if action in subs:
            yield from _walk(subs[action])
        elif not action.isSeparator():
            yield action


# ── the menus ───────────────────────────────────────────────────

def test_the_menu_bar_is_file_edit_view_help(win):
    titles = [a.text().replace("&", "") for a in win.menuBar().actions()]
    assert titles == ["File", "Edit", "View", "Help"]


def test_the_file_menu(win):
    assert _texts(_menu(win, "File")) == [
        "New", "Open…", "Open recent", "Examples", "Save", "Save as…",
        "Export", "Quit"]
    shortcuts = {a.text().replace("&", ""): a.shortcut().toString()
                 for a in _menu(win, "File").actions()}
    assert shortcuts["New"] == "Ctrl+N"          # not a submenu yet (R7)
    assert win._act_file_new.menuRole() == QAction.TextHeuristicRole
    assert shortcuts["Open…"] == "Ctrl+O"
    assert shortcuts["Save"] == "Ctrl+S"
    assert shortcuts["Save as…"] == "Ctrl+Shift+S"
    assert shortcuts["Quit"] == "Ctrl+Q"


def test_export_is_a_file_submenu_with_the_six_items(win):
    export = _submenu(_menu(win, "File"), "Export")
    assert _texts(export) == [
        "Copy analysis report", "Save analysis report…",
        "Export pane as PNG…", "Model diagram…", "Print model diagram…",
        "Model scope data…"]
    assert win._act_export_png.shortcut().toString() == "Ctrl+Shift+E"
    assert export.actions()[0].shortcut().toString() == "Ctrl+Shift+C"


def test_ctrl_shift_p_belongs_to_search_alone(win):
    owners = [a for menu in
              (_menu(win, t) for t in ("File", "Edit", "View", "Help"))
              for a in _walk(menu)
              if "Ctrl+Shift+P" in [k.toString() for k in a.shortcuts()]]
    assert owners == [win._act_search]


def test_the_edit_menu(win):
    edit = _menu(win, "Edit")
    assert _texts(edit) == ["Undo", "Redo", "Send loop to the console",
                            "Preferences…"]
    prefs = win._act_preferences
    assert prefs.shortcut().toString() == "Ctrl+,"
    assert prefs.menuRole() == QAction.PreferencesRole


def test_the_view_menu(win):
    # R5 puts Search… at the top.
    assert _texts(_menu(win, "View")) == [
        "Search…", "Side panel", "Cedric", "Analyse", "Model", "Console",
        "Snapshot bar", "Block palette", "Reset layout"]
    assert win._act_palette.shortcut().toString() == "Ctrl+B"
    assert win._act_side.shortcut().toString() == "Ctrl+\\"


def test_the_help_menu(win):
    help_menu = _menu(win, "Help")
    assert _texts(help_menu) == [
        "Documentation", "Keyboard shortcuts", "Check for updates…", "About"]
    assert help_menu.actions()[0].shortcut().toString() == "F1"


def test_no_two_menu_actions_share_a_shortcut(win):
    seen: dict[str, str] = {}
    for title in ("File", "Edit", "View", "Help"):
        for action in _walk(_menu(win, title)):
            for shortcut in action.shortcuts():
                key = shortcut.toString()
                assert key not in seen, (key, seen[key], action.text())
                seen[key] = action.text()
    # And none on the Model toolbar either (Ctrl+B moved to the View menu).
    for action in win._sim_tab.findChildren(QAction):
        for shortcut in action.shortcuts():
            assert shortcut.toString() not in seen, (
                shortcut.toString(), action.text())


def test_the_block_palette_item_follows_the_model_palette(app, win):
    win.show_workspace(Workspace.MODEL)
    _settle(app, 5)
    assert win._act_palette.isChecked()
    win._act_palette.trigger()
    assert not win._sim_tab.palette_visible
    win._sim_tab.set_palette_visible(True)
    assert win._act_palette.isChecked()


def test_the_snapshot_bar_item_and_preferences_agree(app, win):
    prefs = win.preferences_dialog()
    try:
        win._act_snapshot_bar.trigger()
        assert not win._snapshot_bar.isVisible() and not persist.snapshot_bar()
        assert not prefs.snapshot_bar.isChecked()
        prefs.snapshot_bar.setChecked(True)
        _settle(app, 5)
        assert win._snapshot_bar.isVisible() and persist.snapshot_bar()
        assert win._act_snapshot_bar.isChecked()
    finally:
        win.set_snapshot_bar_visible(True)


# ── nothing that was removed is lost ────────────────────────────

def test_the_plant_menu_holds_the_presets(win):
    menu = win._context._plant_btn.menu()
    assert menu is not None
    names = [a.text() for a in menu.actions() if not a.isSeparator()]
    assert len(names) == 7 + 1                  # seven presets, then the submenu
    assert names[-1] == "From the console workspace…"
    before = session_dict(win._arch)
    menu.actions()[1].trigger()                  # 2nd order underdamped
    assert session_dict(win._arch) != before
    assert win._loop_undo.undoText() == "Load preset"
    win._loop_undo.undo()
    assert session_dict(win._arch) == before


def test_the_plant_menu_lists_the_consoles_systems(win):
    win._console.push(Gplant=ctl.tf([2], [1, 4]), notasystem=3)
    win._console_systems_menu.aboutToShow.emit()
    names = [a.text() for a in win._console_systems_menu.actions()]
    assert "Gplant" in names and "notasystem" not in names
    win._console_systems_menu.actions()[names.index("Gplant")].trigger()
    assert float(ctl.dcgain(win._arch.block_tf("G"))) == pytest.approx(0.5)
    assert win._stack.current is Workspace.ANALYSE
    assert win._loop_undo.undoText() == "Load Gplant as G"
    win._console.interpreter.namespace.pop("Gplant", None)
    win._console.interpreter.namespace.pop("notasystem", None)


def test_send_loop_to_the_console_is_in_the_edit_menu(win):
    win._act_send_loop.trigger()
    assert win._stack.current is Workspace.CONSOLE
    assert "L" in win._console.interpreter.variables()


# ── Preferences ─────────────────────────────────────────────────

def test_the_dialog_is_built_not_shown_and_not_modal(app, win):
    dialog = preferences_dialog(win)
    assert isinstance(dialog, PreferencesDialog)
    assert not dialog.isVisible() and not dialog.isModal()
    dialog.deleteLater()
    shown = win.show_preferences()
    assert shown is win.preferences_dialog() and shown.isVisible()
    assert not shown.isModal()
    shown.close()


def test_every_control_has_an_accessible_name(win):
    dialog = win.preferences_dialog()
    for control in (dialog.startup, dialog.autosave, dialog.autosave_interval,
                    dialog.auto_update, dialog.theme, dialog.title_bar,
                    dialog.classic_boxes, dialog.snapshot_bar, dialog.scope_in):
        assert control.accessibleName(), control


def test_on_launch_is_saved(win):
    dialog = win.preferences_dialog()
    persist.settings().remove(persist.STARTUP_SHOW_KEY)
    try:
        assert persist.startup_show() == "start"
        dialog.startup.setCurrentIndex(dialog.startup.findData("reopen"))
        assert persist.startup_show() == "reopen"
        dialog.sync()
        assert dialog.startup.currentData() == "reopen"
    finally:
        persist.settings().remove(persist.STARTUP_SHOW_KEY)


def test_scope_opens_in_is_saved(win):
    dialog = win.preferences_dialog()
    persist.settings().remove(persist.SCOPE_OPENS_IN_KEY)
    try:
        assert persist.scope_opens_in() == "window"
        dialog.scope_in.setCurrentIndex(dialog.scope_in.findData("panel"))
        assert persist.scope_opens_in() == "panel"
    finally:
        persist.settings().remove(persist.SCOPE_OPENS_IN_KEY)
    persist.settings().setValue(persist.SCOPE_OPENS_IN_KEY, "nonsense")
    try:
        assert persist.scope_opens_in() == "window"
        with pytest.raises(ValueError):
            persist.set_scope_opens_in("nonsense")
    finally:
        persist.settings().remove(persist.SCOPE_OPENS_IN_KEY)


def test_update_checks_follow_the_checkbox(win):
    dialog = win.preferences_dialog()
    before = persist.update_auto_check()
    try:
        dialog.auto_update.setChecked(not before)
        assert persist.update_auto_check() is (not before)
    finally:
        persist.set_update_auto_check(before)
        dialog.sync()


def test_the_interval_only_matters_while_autosave_is_on(win):
    from evans.ui import recovery

    dialog = win.preferences_dialog()
    try:
        dialog.autosave.setChecked(False)
        assert not dialog.autosave_interval.isEnabled()
        dialog.autosave.setChecked(True)
        assert dialog.autosave_interval.isEnabled()
    finally:
        recovery.remember(True, recovery.DEFAULT_INTERVAL)
        win._autosave_enabled = True
        win._autosave_interval = recovery.DEFAULT_INTERVAL
        dialog.sync()


def test_the_dialog_follows_changes_made_elsewhere(win):
    dialog = win.preferences_dialog()
    try:
        win.set_snapshot_bar_visible(False)
        assert not dialog.snapshot_bar.isChecked()
    finally:
        win.set_snapshot_bar_visible(True)
    assert dialog.snapshot_bar.isChecked()


# ── the bottom bar ──────────────────────────────────────────────

def test_the_lamp_is_visible_on_analyse_only(app, win):
    lamp = win._loop_status
    assert lamp.parent() is win.statusBar()
    win.show_workspace(Workspace.ANALYSE)
    _settle(app, 5)
    assert lamp.isVisible()
    for workspace in (Workspace.MODEL, Workspace.CONSOLE):
        win.show_workspace(workspace)
        _settle(app, 5)
        assert not lamp.isVisible(), workspace


def test_the_lamp_survives_a_transient_message(app, win):
    win.show_workspace(Workspace.ANALYSE)
    win._status.showMessage("Something happened", 5000)
    _settle(app, 5)
    assert win._loop_status.isVisible()
    assert win._status.currentMessage() == "Something happened"


def test_the_lamp_and_margins_move_out_of_the_context_bar(win):
    bar = win._context
    assert not bar.isAncestorOf(win._loop_status)
    assert win._loop_status is bar.status
    assert win._loop_status._badge.parent() is win._loop_status
    # What it still answers, through the bar.
    assert bar.verdict is win._loop_status.verdict


def test_the_lamp_explains_itself_in_its_tooltip(app, win):
    win._arch.set_block("G", ctl.tf([1], [1, -1]))
    win._arch.set_block("K2", ctl.tf([0.1], [1]))
    win._context.refresh()
    status = win._loop_status
    assert status.verdict is Status.CRITICAL
    assert "right half plane" in status._badge.toolTip()
    assert status._badge.toolTip() == status.note
    assert "right half plane" in win._context.summary()
    win._arch.set_block("G", ctl.tf([1], [1, 1]))
    win._arch.set_block("K2", unity())
    win._context.refresh()
    assert status.verdict is Status.OK and status._badge.toolTip() == ""


def test_the_margins_are_in_the_status_bar(app, win):
    win._arch.set_block("G", ctl.tf([10], [1, 1, 0]))
    win._arch.set_block("K2", unity())
    win._context.refresh()
    _settle(app, 3)
    text = win._loop_status.margins()
    assert "PM" in text and "GM" in text and "ωc" in text
    assert "nan" not in text
    assert "PM" in win._context.describe()


def test_the_console_says_idle_or_running(app, win):
    label = win._console_state_label
    win.show_workspace(Workspace.CONSOLE)
    _settle(app, 5)
    assert label.isVisible() and label.text() == "Idle"
    win._console.run_state_changed.emit(True)
    assert label.text() == "Running"
    win._console.run_state_changed.emit(False)
    assert label.text() == "Idle"
    for workspace in (Workspace.ANALYSE, Workspace.MODEL):
        win.show_workspace(workspace)
        _settle(app, 5)
        assert not label.isVisible(), workspace


def test_a_console_command_flips_the_label_while_it_runs(app, win):
    states = []
    win._console.run_state_changed.connect(states.append)
    win._console.execute("x = 1;")
    assert states[:1] == [True] or True in states
    assert states[-1] is False
    assert win._console_state_label.text() == "Idle"


def test_the_model_status_still_shows_on_model(app, win):
    status, file_label = win._sim_tab.status_widgets()
    win.show_workspace(Workspace.MODEL)
    _settle(app, 5)
    assert file_label.isVisible()
    win.show_workspace(Workspace.ANALYSE)
    _settle(app, 5)
    assert not file_label.isVisible()


# ── the context bar ─────────────────────────────────────────────

def _long_loop(win):
    roots = [-(k + 1) for k in range(9)]
    den = np.poly(roots)
    win._arch.set_block("G", ctl.tf([1.0], den))
    win._arch.set_block("K2", ctl.tf(np.poly([-0.5, -1.5, -2.5, -3.5]),
                                     np.poly([-0.1, -10.0, -20.0, -30.0, 0.0])))
    win._context.refresh()


def test_the_context_bar_holds_only_the_loop_and_two_buttons(win):
    from PySide6.QtWidgets import QAbstractButton

    bar = win._context
    buttons = {b.accessibleName() for b in bar.findChildren(QAbstractButton)}
    assert buttons == {"Plant", "Edit loop"}
    assert not bar.findChildren(type(win._loop_status._badge))
    assert bar._plant_btn.x() < bar._edit_btn.x()       # Plant is left of Edit loop


def test_a_short_loop_is_one_line_at_1280(app, win):
    win._arch.set_block("G", ctl.tf([1], [1, 1]))
    win._arch.set_block("K2", unity())
    win.resize(TARGET_W, TARGET_H)
    win._context.refresh()
    _settle(app)
    assert not win._context.stacked
    assert win._context._plant.y() == win._context._controller.y()


def test_a_long_loop_is_two_lines_and_the_window_still_fits(app, win):
    win.set_side_panel_open(True)
    win._side_panels[Workspace.ANALYSE].set_current("loop")
    _long_loop(win)
    win.resize(TARGET_W, TARGET_H)
    _settle(app)
    bar = win._context
    assert bar.stacked
    assert bar._controller.y() > bar._plant.y()
    hint = win.minimumSizeHint()
    assert hint.width() <= TARGET_W, hint
    assert hint.height() <= TARGET_H, hint
    assert (win.width(), win.height()) == (TARGET_W, TARGET_H)
    # The whole of it is still the text and the tooltip.
    assert bar._plant.text().startswith("G(s)")
    assert bar._plant.toolTip() == bar._plant.text()


def test_a_long_loop_is_cut_short_not_widening_the_bar(app, win):
    _long_loop(win)
    win.resize(TARGET_W, TARGET_H)
    _settle(app)
    plant = win._context._plant
    assert plant.fontMetrics().horizontalAdvance(plant.text()) > plant.width() \
        or win._context.stacked
    assert plant.minimumSizeHint().width() < 300
    assert win._context.minimumSizeHint().width() < 700


def test_the_bar_goes_back_to_one_line_when_the_loop_gets_short(app, win):
    _long_loop(win)
    win.resize(TARGET_W, TARGET_H)
    _settle(app)
    assert win._context.stacked
    win._arch.set_block("G", ctl.tf([1], [1, 1]))
    win._arch.set_block("K2", unity())
    win._context.refresh()
    _settle(app)
    assert not win._context.stacked
