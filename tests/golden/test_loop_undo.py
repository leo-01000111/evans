"""
Undo for the loop on Analyse, and the Edit menu that serves both stacks.

The command itself is plain Qt; what these tests pin is the wiring: every
change to G, K1, K2 or H goes through `MainWindow.change_loop` and is one
step, the architecture object never changes, and Edit > Undo acts on the
stack of the workspace in view.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="Qt not available")

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from evans.core.architecture import CourseArchitecture
from evans.core.session import session_dict
from evans.core.tf_utils import first_order, second_order, unity
from evans.ui.loop_undo import ReplaceLoop
from evans.ui.mainwindow import MainWindow
from evans.ui.workspace import Workspace


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def win(app):
    window = MainWindow(CourseArchitecture(G=second_order(1.0, 0.5, 2.0)))
    window.resize(1500, 900)
    window.show()
    _settle(app)
    yield window
    window.hide()


@pytest.fixture(autouse=True)
def reset(request, app):
    if "win" not in request.fixturenames:
        yield
        return
    window = request.getfixturevalue("win")
    window.show_workspace(Workspace.ANALYSE)
    window._loop_undo.clear()
    window._sim_tab._canvas.undo_stack.clear()
    window.snapshots.clear()
    window._snapshot_bar.refresh()
    window._arch.set_block("G", second_order(1.0, 0.5, 2.0))
    window._arch.set_block("K2", unity())
    window._after_loop_change()
    window._loop_undo.clear()
    yield
    window.show_workspace(Workspace.ANALYSE)


def _settle(app, rounds: int = 20) -> None:
    for _ in range(rounds):
        app.processEvents()


def _g(win):
    return session_dict(win._arch)["blocks"]["G"]


# ── the command ───────────────────────────────────────────────

def test_first_redo_does_nothing_then_undo_and_redo_swap_the_loop():
    arch = CourseArchitecture(G=first_order(1.0, 1.0))
    before = session_dict(arch)
    arch.set_block("G", second_order(1.0, 0.5, 2.0))
    after = session_dict(arch)
    calls = []
    command = ReplaceLoop(arch, before, after, "x", lambda: calls.append(1))
    command.redo()
    assert session_dict(arch) == after and not calls
    command.undo()
    assert session_dict(arch) == before and len(calls) == 1
    command.redo()
    assert session_dict(arch) == after and len(calls) == 2


# ── window behaviour ──────────────────────────────────────────

def test_editing_g_then_undo_restores_the_plant_and_every_pane(app, win):
    old = _g(win)
    win._editor.tf_changed.emit("G", first_order(3.0, 4.0))
    assert _g(win) != old
    assert win._loop_undo.undoText() == "Edit G"
    win._loop_undo.undo()
    _settle(app)
    assert _g(win) == old
    assert np.allclose(win._arch.block_tf("G").den[0][0],
                       second_order(1.0, 0.5, 2.0).den[0][0])
    # The diagram and the context bar follow the architecture.
    assert win._diagram._arch is win._arch
    win._loop_undo.redo()
    assert _g(win) != old


def test_a_preset_is_one_step(win):
    win._preset_so_over()
    assert win._loop_undo.count() == 1
    assert win._loop_undo.undoText() == "Load preset"
    win._loop_undo.undo()
    assert _g(win) == session_dict(
        CourseArchitecture(G=second_order(1.0, 0.5, 2.0)))["blocks"]["G"]


def test_a_snapshot_restore_is_one_step(win):
    win._snapshot_bar.take("before")
    win._arch.set_block("G", first_order(5.0, 1.0))
    win.change_loop("Edit G")
    assert win._loop_undo.count() == 1
    win._snapshot_bar.restore()
    assert win._loop_undo.count() == 2
    assert win._loop_undo.undoText() == "Restore snapshot"
    win._loop_undo.undo()
    assert np.allclose(win._arch.block_tf("G").num[0][0], [5.0])


def test_linearising_is_one_step_and_resets_k2(win):
    win._arch.set_block("K2", first_order(2.0, 1.0))
    win.change_loop("Edit K2")
    win._loop_undo.clear()
    win._on_linearised(first_order(7.0, 2.0), "a model\nmore")
    assert win._loop_undo.count() == 1
    assert win._loop_undo.undoText() == "Load linearised model"
    win._loop_undo.undo()
    assert not np.allclose(win._arch.block_tf("G").num[0][0], [7.0])
    assert np.allclose(win._arch.block_tf("K2").den[0][0], [1.0, 1.0])


def test_the_controller_the_design_tab_applied_is_undoable(win):
    # The tab writes the architecture first, then tells the window.
    tf = first_order(4.0, 0.5)
    win._arch.set_block("K2", tf)
    win._on_controller_designed(tf)
    assert win._loop_undo.undoText() == "Apply controller"
    win._loop_undo.undo()
    assert np.allclose(win._arch.block_tf("K2").num[0][0], [1.0])


def test_ten_merged_changes_are_one_step(win):
    for gain in range(1, 11):
        win.change_loop("Slider", lambda g=gain: win._arch.set_block(
            "G", first_order(float(g), 1.0)), merge_key="slider")
    assert win._loop_undo.count() == 1
    win._loop_undo.undo()
    assert _g(win) == session_dict(
        CourseArchitecture(G=second_order(1.0, 0.5, 2.0)))["blocks"]["G"]
    win._loop_undo.redo()
    assert np.allclose(win._arch.block_tf("G").num[0][0], [10.0])


def test_different_merge_keys_stay_separate_steps(win):
    win.change_loop("a", lambda: win._arch.set_block(
        "G", first_order(2.0, 1.0)), merge_key="a")
    win.change_loop("b", lambda: win._arch.set_block(
        "G", first_order(3.0, 1.0)), merge_key="b")
    assert win._loop_undo.count() == 2


def test_a_change_that_changes_nothing_adds_no_step(win):
    win.change_loop("noop", lambda: None)
    assert win._loop_undo.count() == 0


def test_a_console_command_that_changes_arch_is_undoable(win):
    before = _g(win)
    win._console.execute("arch.set_block('G', tf(9, [1 1]))")
    assert win._loop_undo.count() == 1
    assert win._loop_undo.undoText() == "Console change"
    assert _g(win) != before
    win._loop_undo.undo()
    assert _g(win) == before


def test_a_console_command_that_leaves_arch_alone_adds_no_step(win):
    win._console.execute("x = 1 + 1")
    assert win._loop_undo.count() == 0


def test_a_new_session_keeps_the_same_architecture_object(win):
    arch = win._arch
    win._new_session()
    assert win._arch is arch
    assert win._diagram._arch is arch
    assert win._snapshot_bar._arch is arch
    assert win._console.interpreter.namespace["arch"] is arch
    assert win._loop_undo.undoText() == "New loop"
    win._loop_undo.undo()
    assert win._arch is arch
    assert np.allclose(arch.block_tf("G").den[0][0],
                       second_order(1.0, 0.5, 2.0).den[0][0])


# ── the Edit menu ─────────────────────────────────────────────

def test_edit_menu_sits_after_file_with_undo_and_redo(win):
    titles = [a.text().replace("&", "") for a in win.menuBar().actions()]
    assert titles[:2] == ["File", "Edit"]
    assert win._edit_menu.actions()[0] is win._act_undo
    assert win._edit_menu.actions()[1] is win._act_redo


def test_the_menu_undoes_the_loop_on_analyse(win):
    win._preset_so_over()
    assert win._act_undo.isEnabled()
    win._act_undo.trigger()
    assert win._loop_undo.count() == 1 and not win._loop_undo.canUndo()
    assert win._act_redo.isEnabled()
    win._act_redo.trigger()
    assert win._loop_undo.canUndo()


def test_the_menu_acts_on_the_canvas_when_model_is_current(app, win):
    canvas = win._sim_tab._canvas
    win.show_workspace(Workspace.MODEL)
    canvas.add_block("Gain")
    blocks = len(canvas.model.blocks)
    assert win._act_undo.isEnabled()
    win._act_undo.trigger()
    assert len(canvas.model.blocks) == blocks - 1
    win._act_redo.trigger()
    assert len(canvas.model.blocks) == blocks
    # The loop stack is untouched by it, and not what the menu serves here.
    assert win._loop_undo.count() == 0
    # The toolbar buttons still drive the canvas stack.
    canvas.undo_stack.undo()
    assert len(canvas.model.blocks) == blocks - 1


def test_the_menu_has_no_stack_on_the_console(win):
    win._preset_so_over()
    win.show_workspace(Workspace.CONSOLE)
    assert win._undo_group.activeStack() is None
    assert not win._act_undo.isEnabled()
    win.show_workspace(Workspace.ANALYSE)
    assert win._act_undo.isEnabled()


def test_the_model_toolbar_no_longer_owns_ctrl_z(win):
    bar_actions = {a.text(): a for a in win._sim_tab.findChildren(
        type(win._act_undo)) if a.text() in ("Undo", "Redo")}
    for name in ("Undo", "Redo"):
        for action in win._sim_tab.findChildren(type(win._act_undo)):
            if action.text() == name:
                assert action.shortcut().isEmpty()
    assert bar_actions
    assert win._act_undo.shortcut().toString() == "Ctrl+Z"
    assert "Ctrl+Y" in [s.toString() for s in win._act_redo.shortcuts()]


def test_the_menu_follows_the_canvas_into_a_subsystem(win):
    canvas = win._sim_tab._canvas
    win.show_workspace(Workspace.MODEL)
    outer = canvas.undo_stack
    assert win._undo_group.activeStack() is outer
    canvas.add_block("Subsystem")
    sub_id = next(b for b, blk in canvas.model.blocks.items()
                  if blk.type_name == "Subsystem")
    canvas.descend(sub_id)
    assert canvas.undo_stack is not outer
    assert win._undo_group.activeStack() is canvas.undo_stack
    canvas.add_block("Gain")
    win._act_undo.trigger()
    assert not canvas.undo_stack.canUndo()
    canvas.ascend()
    assert win._undo_group.activeStack() is outer


def test_an_undo_says_so_in_the_bottom_bar(win):
    win._preset_so_over()
    win._status.clearMessage()
    win._loop_undo.undo()
    assert win._status.currentMessage() == "Undo: Load preset"


# ── typing keeps its own undo ─────────────────────────────────

def test_ctrl_z_in_the_script_editor_still_undoes_typing(app, win):
    win.show_workspace(Workspace.CONSOLE)
    _settle(app)
    console = win._console
    console._tabs.setCurrentWidget(console.editor)
    _settle(app)
    code = console.editor.current_document().code
    code.setPlainText("")
    code.document().clearUndoRedoStacks()
    code.setFocus()
    QTest.keyClicks(code, "abc")
    assert code.toPlainText() == "abc"
    QTest.keyClick(code, Qt.Key_Z, Qt.ControlModifier)
    assert code.toPlainText() != "abc"
    code.setPlainText("")
    console._tabs.setCurrentIndex(0)
