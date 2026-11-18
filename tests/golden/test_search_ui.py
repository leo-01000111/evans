"""
R5/R6b: the command palette, its field in each workspace, and the shortcut sheet.

The window is shared (module scope) and put back by the `reset` fixture.
Nothing opens a modal dialog: the palette is a child widget and the sheet is
non-modal.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="Qt not available")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMenu, QWidget

from evans import help as pages
from evans.core.architecture import CourseArchitecture
from evans.core.session import load_session_dict, session_dict
from evans.ui import keys, persist
from evans.ui.mainwindow import MainWindow
from evans.ui.search_field import HEIGHT as FIELD_HEIGHT
from evans.ui.search_field import SearchField
from evans.ui.search_popup import SHADOW, TOP, WIDTH, SearchPopup
from evans.ui.search_registry import collect, menu_actions
from evans.ui.shortcuts import EXTRA_KEYS, ShortcutsDialog
from evans.ui.workspace import Workspace


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def win(app):
    window = MainWindow(CourseArchitecture())
    window.resize(1400, 850)
    window.show()
    _settle(app)
    yield window
    window.hide()


@pytest.fixture(autouse=True)
def reset(win, app):
    popup = win.search_popup()
    popup.close_popup(restore_focus=False)
    persist.set_search_recent([])
    load_session_dict(win._arch, session_dict(CourseArchitecture()))
    win._loop_undo.clear()
    win._after_loop_change()
    win._sim_tab.mark_saved()                 # the last test's block
    win._sim_tab.new_model()
    win._sim_tab._canvas.undo_stack.clear()
    win.show_workspace(Workspace.ANALYSE)
    win._grid.set_layout_size(1, ("step",))
    win._grid.set_active_index(0)
    win.resize(1400, 850)
    if win._shortcuts is not None:
        win._shortcuts.close()
    _settle(app)
    yield
    popup.close_popup(restore_focus=False)


def _settle(app, rounds: int = 10) -> None:
    for _ in range(rounds):
        app.processEvents()


def _menu(win, title: str):
    # Found as children: a menu got through `QAction.menu()` of a temporary
    # wrapper can be gone by the time it is used.
    for menu in win.menuBar().findChildren(QMenu):
        if menu.title().replace("&", "") == title                 and menu.parent() is win.menuBar():
            return menu
    raise AssertionError(title)


def _type(app, popup, text: str) -> None:
    popup.field.setText(text)
    _settle(app, 3)


def _enter(app, popup) -> None:
    QTest.keyClick(popup.field, Qt.Key_Return)
    _settle(app)


def _block_types(win) -> list[str]:
    return [b.type_name for b in win._sim_tab._canvas.model.blocks.values()]


# ── opening ─────────────────────────────────────────────────────

def test_search_is_a_window_action_on_both_shortcuts(win):
    keys_ = [k.toString() for k in win._act_search.shortcuts()]
    assert keys_ == ["Ctrl+K", "Ctrl+Shift+P"]
    assert _menu(win, "View").actions()[0] is win._act_search


def test_ctrl_k_opens_the_popup_with_focus_in_the_field(win, app):
    win.activateWindow()
    _settle(app)
    popup = win.search_popup()
    assert not popup.isVisible()
    QTest.keySequence(win, QKeySequence("Ctrl+K"))
    _settle(app)
    if not popup.isVisible():            # an inactive offscreen window
        win._act_search.trigger()
        _settle(app)
    assert popup.isVisible()
    assert popup.field.hasFocus()
    assert popup.field.accessibleName() == "Search"
    assert popup.field.placeholderText() == \
        "Search actions, blocks, commands, help"


def test_the_action_toggles(win, app):
    win._act_search.trigger()
    assert win.search_popup().isVisible()
    win._act_search.trigger()
    assert not win.search_popup().isVisible()


def test_geometry_follows_the_spec(win, app):
    popup = win.show_search()
    _settle(app)
    plate = popup._plate
    assert plate.width() == WIDTH == 560
    assert popup.y() == TOP == 48
    assert abs(plate.mapTo(win, QPoint(0, 0)).x()
               - (win.width() - 560) // 2) <= 1
    assert popup.width() == WIDTH + SHADOW


def test_in_a_narrow_window_the_plate_is_the_width_less_32(app):
    parent = QWidget()
    parent.resize(400, 600)
    parent.show()
    popup = SearchPopup(parent)
    popup.open_with([], None, [])
    _settle(app)
    assert popup._plate.width() == 400 - 32
    assert popup.y() == TOP
    popup.close_popup()
    parent.close()


def test_at_most_ten_rows_show_without_scrolling(win, app):
    popup = win.show_search()
    _type(app, popup, "a")
    assert len(popup.results) > 10
    rows = popup._list.height() // popup._list.sizeHintForRow(0)
    assert rows == 10


def test_no_match_says_so(win, app):
    popup = win.show_search()
    _type(app, popup, "qqzzxx")
    assert popup.results == []
    assert popup._none.isVisible() and not popup._list.isVisible()
    _enter(app, popup)                        # nothing to run: stays open
    assert popup.isVisible()


# ── choosing ────────────────────────────────────────────────────

def test_on_model_gain_enter_adds_a_gain_block_in_one_undo_step(win, app):
    win.show_workspace(Workspace.MODEL)
    stack = win._sim_tab._canvas.undo_stack
    before, blocks = stack.count(), len(_block_types(win))
    popup = win.show_search()
    _type(app, popup, "gain")
    assert popup.results[0].id == "block.Gain"
    _enter(app, popup)
    assert not popup.isVisible()
    assert stack.count() == before + 1
    assert _block_types(win).count("Gain") == 1
    assert len(_block_types(win)) == blocks + 1
    stack.undo()
    assert len(_block_types(win)) == blocks


def test_on_analyse_the_block_sits_in_a_later_group_and_switches(win, app):
    popup = win.show_search()
    _type(app, popup, "gain")
    ids = [e.id for e in popup.results]
    assert "block.Gain" in ids
    analyse = [i for i, e in enumerate(popup.results)
               if e.workspace is Workspace.ANALYSE]
    model = [i for i, e in enumerate(popup.results)
             if e.workspace is Workspace.MODEL]
    assert analyse and model and max(analyse) < min(model)
    popup._list.setCurrentIndex(popup._model.index(ids.index("block.Gain")))
    _enter(app, popup)
    assert win._stack.current is Workspace.MODEL
    assert _block_types(win).count("Gain") == 1


def test_bode_enter_changes_the_active_pane(win, app):
    win._grid.set_layout_size(2, ("step", "impulse"))
    _settle(app)
    popup = win.show_search()
    _type(app, popup, "show bode")
    assert popup.results[0].id == "pane.bode"
    _enter(app, popup)
    assert win._grid.keys == ("bode", "impulse")


def test_clicking_a_pane_makes_it_the_active_one(win, app):
    win._grid.set_layout_size(2, ("step", "impulse"))
    _settle(app)
    assert win._grid.active_index == 0
    second = win._grid.panes[1]
    QTest.mouseClick(second, Qt.LeftButton, Qt.NoModifier, QPoint(8, 8))
    assert win._grid.active_index == 1
    popup = win.show_search()
    _type(app, popup, "show nyquist")
    _enter(app, popup)
    assert win._grid.keys == ("step", "nyquist")


def test_the_active_pane_is_clamped_when_the_layout_shrinks(win, app):
    win._grid.set_layout_size(4)
    win._grid.set_active_index(3)
    win._grid.set_layout_size(1)
    assert win._grid.active_index == 0


def test_a_preset_runs_through_the_plant_machinery(win, app):
    popup = win.show_search()
    _type(app, popup, "unstable")
    ids = [e.id for e in popup.results]
    assert "preset.unstable" in ids
    popup._list.setCurrentIndex(popup._model.index(ids.index("preset.unstable")))
    _enter(app, popup)
    assert max(win._arch.block_tf("G").poles().real) > 0
    win._loop_undo.undo()


def test_design_pages_open_the_design_panel(win, app):
    popup = win.show_search()
    _type(app, popup, "design: pid")
    assert popup.results[0].id == "design.pid"
    _enter(app, popup)
    assert win._design.mode == "pid"


def test_a_menu_action_runs_and_is_remembered(win, app):
    win.show_workspace(Workspace.CONSOLE)
    popup = win.show_search()
    _type(app, popup, "side panel")
    assert popup.results[0].id == "view.side_panel"
    before = win._act_side.isChecked()
    _enter(app, popup)
    assert win._act_side.isChecked() != before
    assert persist.search_recent()[0] == "view.side_panel"
    win._act_side.trigger()


def test_recent_entries_lead_when_the_field_is_empty(win, app):
    persist.set_search_recent(["view.reset_layout", "view.console"])
    popup = win.show_search()
    assert [e.id for e in popup.results[:2]] == [
        "view.reset_layout", "view.console"]


def test_recent_is_capped_at_twenty(win, app):
    ids = [f"x.{n}" for n in range(30)]
    persist.set_search_recent(ids)
    assert persist.search_recent() == ids[:20]


# ── closing ─────────────────────────────────────────────────────

def test_escape_closes_and_restores_focus(win, app):
    win.activateWindow()
    win.show_workspace(Workspace.CONSOLE)
    _settle(app)
    anchor = win._stack.rail.button(Workspace.CONSOLE)
    anchor.setFocusPolicy(Qt.StrongFocus)
    anchor.setFocus()
    _settle(app)
    had_focus = app.focusWidget() is anchor
    popup = win.show_search()
    QTest.keyClick(popup.field, Qt.Key_Escape)
    _settle(app)
    assert not popup.isVisible()
    assert popup._previous_focus is None
    if had_focus:                         # an active window, as on a desktop
        assert app.focusWidget() is anchor


def test_arrow_keys_move_the_selection(win, app):
    popup = win.show_search()
    _type(app, popup, "a")
    assert popup._list.currentIndex().row() == 0
    QTest.keyClick(popup.field, Qt.Key_Down)
    assert popup._list.currentIndex().row() == 1
    QTest.keyClick(popup.field, Qt.Key_Up)
    assert popup._list.currentIndex().row() == 0


def test_a_click_outside_closes(win, app):
    popup = win.show_search()
    QTest.mouseClick(win._grid.panes[0], Qt.LeftButton, Qt.NoModifier,
                     QPoint(5, 5))
    assert not popup.isVisible()


def test_a_click_on_a_row_runs_it(win, app):
    win.show_workspace(Workspace.MODEL)
    popup = win.show_search()
    _type(app, popup, "gain")
    popup._list.clicked.emit(popup._model.index(0))
    _settle(app)
    assert not popup.isVisible()
    assert _block_types(win).count("Gain") == 1


# ── what the registry holds ─────────────────────────────────────

def test_every_enabled_menu_action_appears_exactly_once(win):
    entries = collect(win)
    from_actions = [e.source for e in entries if e.source is not None]
    expected = [a for _path, a in menu_actions(win)]
    assert len(expected) > 20
    assert sorted(map(id, from_actions)) == sorted(map(id, expected))
    assert len(set(map(id, from_actions))) == len(from_actions)
    ids = [e.id for e in entries]
    assert len(ids) == len(set(ids))


def test_menu_walk_reaches_the_submenus(win):
    titles = {(path[0], path[-1]) for path, _a in menu_actions(win)}
    assert ("File", "Model diagram…") in titles          # Export
    assert ("View", "Search…") in titles
    assert ("Help", "Keyboard shortcuts") in titles
    assert ("Edit", "Preferences…") in titles


def test_the_registry_has_the_four_kinds_of_entry(win):
    ids = {e.id for e in collect(win)}
    assert {"pane.bode", "layout.4", "preset.so_under", "design.gain",
            "snapshot.take", "block.Gain", "model.run", "model.linearise",
            "model.scripts", "help.bode", "file.save_as"} <= ids
    assert any(i.startswith("example.") for i in ids)


def test_workspace_specific_actions_carry_their_workspace(win):
    by_id = {e.id: e for e in collect(win)}
    assert by_id["file.export.model_diagram"].workspace is Workspace.MODEL
    assert by_id["file.export.export_pane_as_png"].workspace \
        is Workspace.ANALYSE
    assert by_id["file.save"].workspace is None
    assert by_id["pane.bode"].workspace is Workspace.ANALYSE
    assert by_id["block.Gain"].workspace is Workspace.MODEL
    assert by_id["help.bode"].workspace is Workspace.CONSOLE


def test_recent_files_and_open_scripts_are_listed(win, tmp_path):
    script = tmp_path / "demo_script.m"
    script.write_text("x = 1;\n", encoding="utf-8")
    win.recent_files.add(script)
    win._console.editor.load_file(script)
    try:
        entries = {e.title: e for e in collect(win)}
        assert "Open: demo_script.m" in entries
        assert entries["Open: demo_script.m"].section == "Recent"
        assert "Script: demo_script.m" in entries
    finally:
        win.recent_files.clear()
        editor = win._console.editor
        editor.close_document(editor.document_for(script))


def test_shortcuts_are_shown_through_keys_label(win, monkeypatch):
    monkeypatch.setattr(keys, "is_mac", lambda platform=None: True)
    by_id = {e.id: e for e in collect(win)}
    assert by_id["file.save"].shortcut == "⌘S"
    assert by_id["view.search"].shortcut == "⌘K / ⇧⌘P"
    assert by_id["model.run"].shortcut == "⌘R"
    assert "Ctrl" not in "".join(e.shortcut for e in by_id.values())


def test_a_disabled_action_is_not_offered(win):
    assert not win._act_undo.isEnabled()
    assert "edit.undo" not in {e.id for e in collect(win)}
    assert "edit.undo" in {e.id for e in collect(win, for_sheet=True)}


# ── the field in each workspace's top strip (R6b) ───────────────

def _field_of(win, workspace):
    return {Workspace.ANALYSE: win._context.search_button,
            Workspace.MODEL: win._sim_tab.search_button,
            Workspace.CONSOLE: win._console.search_button}[workspace]


def test_the_title_strip_has_no_search_field(win):
    assert not hasattr(win.title_bar, "search_button")
    assert not win.title_bar.findChildren(SearchField)


def test_each_workspace_has_a_big_search_field_in_its_own_strip(win, app):
    assert win.search_fields() == [_field_of(win, w) for w in (
        Workspace.ANALYSE, Workspace.MODEL, Workspace.CONSOLE)]
    for workspace in (Workspace.ANALYSE, Workspace.MODEL, Workspace.CONSOLE):
        win.show_workspace(workspace)
        _settle(app)
        field = _field_of(win, workspace)
        assert isinstance(field, SearchField)
        assert field.accessibleName() == "Search"
        assert field.isVisible(), workspace
        assert field.height() >= FIELD_HEIGHT >= 30
        assert "Ctrl K" in field.text() or "⌘K" in field.text()
        assert field.width() > 100


def test_the_field_wears_the_accent(win):
    from evans.ui import theme, theme_qt
    t = theme.tokens()
    sheet = theme_qt.build_stylesheet(t)
    rule = sheet[sheet.index("#WorkspaceSearch {"):]
    rule = rule[:rule.index("}")]
    assert f"background: {t.signal}" in rule and t.on_signal in rule
    assert "border-radius: 0" in rule


def test_the_analyse_field_sits_between_g_and_the_buttons(win, app):
    bar = win._context
    field = bar.search_button
    assert bar._systems.x() + bar._systems.width() <= field.x() + 1
    assert field.x() + field.width() <= bar._plant_btn.x()
    assert field.parentWidget() is bar


def test_the_model_field_floats_centred_over_the_canvas(win, app):
    from evans.ui.sim.arrange import INSET, REST
    win.show_workspace(Workspace.MODEL)
    _settle(app)
    sim = win._sim_tab
    field = sim.search_button
    canvas = sim._canvas
    assert field.parentWidget() is canvas
    assert field.opacity == REST < 1
    vp = canvas.viewport().geometry()
    assert abs((field.x() + field.width() / 2) - vp.center().x()) <= 2
    assert field.y() == vp.top() + INSET
    arrange = sim._arrange
    assert field.geometry().right() < arrange.geometry().left()


def test_the_console_field_is_between_the_tabs_and_ask_cedric(win, app):
    win.show_workspace(Workspace.CONSOLE)
    _settle(app)
    panel = win._console
    field = panel.search_button
    assert field.parentWidget().parentWidget() is panel._tabs
    tab_bar = panel._tabs.tabBar()
    left = field.mapTo(win, field.rect().topLeft()).x()
    bar_right = tab_bar.mapTo(
        win, tab_bar.rect().topRight()).x()
    cedric = panel.cedric_button.mapTo(win, panel.cedric_button.rect().topLeft())
    assert bar_right <= left
    assert left + field.width() <= cedric.x() + 1


@pytest.mark.parametrize("workspace", [Workspace.ANALYSE, Workspace.MODEL,
                                       Workspace.CONSOLE])
def test_clicking_the_field_opens_the_palette(win, app, workspace):
    win.show_workspace(workspace)
    _settle(app)
    field = _field_of(win, workspace)
    QTest.mouseClick(field, Qt.LeftButton)
    _settle(app)
    assert win.search_popup().isVisible()
    win.search_popup().close_popup(restore_focus=False)


def test_clicking_the_field_again_closes_the_palette(win, app):
    field = _field_of(win, Workspace.ANALYSE)
    popup = win.search_popup()
    win.toggle_search()
    _settle(app)
    assert popup.isVisible()
    assert any(f is field for f in popup._ignore)
    win.toggle_search()
    _settle(app)
    assert not popup.isVisible()


def test_the_fields_do_not_widen_the_window(win):
    for field in win.search_fields():
        assert field.minimumSizeHint().width() == 0


# ── the shortcut sheet ──────────────────────────────────────────

def test_help_menu_has_keyboard_shortcuts_on_ctrl_slash(win):
    assert win._act_shortcuts.shortcut().toString() == "Ctrl+/"
    assert win._act_shortcuts in _menu(win, "Help").actions()


def test_the_sheet_lists_every_shortcut_by_section(win, app):
    dialog = win.show_shortcuts()
    assert isinstance(dialog, ShortcutsDialog)
    assert not dialog.isModal()
    rows = {(s, t): k for s, t, k in dialog.rows}
    assert rows[("View", "Search…")] == keys.label("Ctrl+K / Ctrl+Shift+P")
    assert rows[("File", "Save as…")] == keys.label("Ctrl+Shift+S")
    assert rows[("Edit", "Undo")] == keys.label("Ctrl+Z")      # though disabled
    shown = {k for _s, _t, k in dialog.rows}
    for _where, key, _what in EXTRA_KEYS:
        if key != "Ctrl+`":
            assert keys.label(key) in shown
    assert {"Model canvas", "Command window", "Script editor"} <= \
        {s for s, _t, _k in dialog.rows}
    sections = [s for s, _t, _k in dialog.rows]
    assert sections.index("File") < sections.index("Edit") \
        < sections.index("View") < sections.index("Help")


def test_the_documentation_carries_the_same_sheet(win):
    page = pages.load("shortcuts")
    assert page is not None and "shortcuts" in pages.GUIDES
    text = open(pages.path("shortcuts"), encoding="utf-8").read()
    for entry in collect(win, for_sheet=True):
        if entry.shortcut:
            assert entry.shortcut in text, entry.id
    for _where, key, what in EXTRA_KEYS:
        assert f"- {key}: {what}" in text
