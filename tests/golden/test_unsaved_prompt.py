"""
Unsaved work on the Model tab and in the live script: the mark that shows it,
and the Save / Discard / Cancel asked before quitting or replacing it.
"""

from __future__ import annotations

import pytest

from evans.ui.unsaved import UNSAVED_MARK

pytest.importorskip("PySide6", reason="Qt not available")


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def window(app):
    from evans.core.architecture import CourseArchitecture
    from evans.core.tf_utils import second_order
    from evans.ui.mainwindow import MainWindow
    window = MainWindow(CourseArchitecture(G=second_order(1.0, 0.5, 2.0)))
    yield window
    window.hide()


@pytest.fixture
def win(window):
    """The window with nothing unsaved and a quit not yet confirmed."""
    from evans.console.live import LiveDocument
    from evans.ui.sim.sim_tab import course_loop

    window._console.live.set_document(LiveDocument([]))
    sim = window._sim_tab
    sim._canvas.set_model(course_loop())
    sim.mark_saved()
    window._quit_confirmed = False
    assert window.recovery_items() == []
    yield window
    window._quit_confirmed = False


def _answer(monkeypatch, owner, *answers):
    """Script ``owner._ask_to_save``; returns the list of questions asked."""
    asked = []
    queue = list(answers)

    def ask(*_args):
        asked.append(owner)
        return queue.pop(0)
    monkeypatch.setattr(owner, "_ask_to_save", ask)
    return asked


def _edit_model(sim, stop=42.0):
    sim._t_end.setValue(stop)            # a run setting, saved with the model


def _edit_live(live, text="z = 7"):
    live._widgets[0].editor.setPlainText(text)
    live._show_unsaved()                 # what the 250 ms timer does


# ── the marks ───────────────────────────────────────────────────


def test_model_mark_appears_on_edit_and_clears_on_save(win, tmp_path,
                                                       monkeypatch):
    sim = win._sim_tab
    assert not sim._file_label.text().endswith(UNSAVED_MARK)
    _edit_model(sim)
    assert sim.is_unsaved()
    assert sim._file_label.text().endswith(UNSAVED_MARK)

    path = tmp_path / "loop.evx"
    monkeypatch.setattr("evans.ui.sim.sim_tab.QFileDialog.getSaveFileName",
                        lambda *a, **k: (str(path), ""))
    sim.save_model()
    assert path.exists()
    assert not sim.is_unsaved()
    assert sim._file_label.text() == "loop.evx"


def test_model_mark_follows_canvas_edits_and_undo(win):
    sim = win._sim_tab
    canvas = sim._canvas
    canvas.add_block("Gain")
    assert sim._file_label.text().endswith(UNSAVED_MARK)
    canvas.undo_stack.undo()
    assert not sim._file_label.text().endswith(UNSAVED_MARK)


def test_live_mark_appears_on_edit_and_clears_on_save(win, tmp_path):
    live = win._console.live
    assert live._path_label.text() == "untitled"
    _edit_live(live)
    assert live._path_label.text() == "untitled" + UNSAVED_MARK

    path = live.save(tmp_path / "lab.m")
    assert path is not None
    assert live._path_label.text() == "lab.m"


def test_live_mark_comes_from_the_edit_without_being_asked(win):
    """Typing starts the check; it runs once the timer fires."""
    live = win._console.live
    live._widgets[0].editor.setPlainText("w = 1")
    assert live._unsaved_check.isActive()
    live._unsaved_check.timeout.emit()
    assert live._path_label.text().endswith(UNSAVED_MARK)


# ── what does not count ─────────────────────────────────────────


def test_running_cells_is_not_an_unsaved_change(win, tmp_path):
    live = win._console.live
    _edit_live(live, "r = 2 + 3")
    live.save(tmp_path / "run.m")
    assert live.run_all()
    assert live.document.cells[0].output is not None
    assert not live.is_unsaved()


def test_running_the_model_is_not_an_unsaved_change(win):
    import time

    from PySide6.QtWidgets import QApplication
    sim = win._sim_tab
    sim._t_end.setValue(1.0)
    sim.mark_saved()
    sim.run_simulation()
    for _ in range(2000):
        if sim._thread is None:
            break
        QApplication.processEvents()
        time.sleep(0.005)
    assert sim._result is not None
    assert not sim.is_unsaved()


def test_quit_with_nothing_unsaved_asks_nothing(win, monkeypatch):
    asked = _answer(monkeypatch, win._sim_tab) + \
        _answer(monkeypatch, win._console.live)
    assert win.confirm_quit()
    assert asked == []


def test_example_opened_then_quit_asks_nothing(win, monkeypatch):
    from evans.examples import examples
    asked_model = _answer(monkeypatch, win._sim_tab)
    asked_live = _answer(monkeypatch, win._console.live)
    assert win.open_example(examples()[0])
    assert not win._sim_tab.is_unsaved()
    assert not win._sim_tab._file_label.text().endswith(UNSAVED_MARK)
    assert win.confirm_quit()
    assert asked_model == asked_live == []


# ── the quit prompt ─────────────────────────────────────────────


def test_quit_cancel_on_the_model_keeps_evans_open(win, monkeypatch):
    _edit_model(win._sim_tab)
    asked = _answer(monkeypatch, win._sim_tab, "cancel")
    assert not win.confirm_quit()
    assert len(asked) == 1
    assert win._sim_tab.is_unsaved()


def test_quit_discard_on_the_model_quits_and_asks_once(win, monkeypatch):
    _edit_model(win._sim_tab)
    asked = _answer(monkeypatch, win._sim_tab, "discard")
    assert win.confirm_quit()
    assert win.confirm_quit()                # the close after a restart
    assert len(asked) == 1


def test_quit_save_on_the_model_writes_it(win, tmp_path, monkeypatch):
    sim = win._sim_tab
    _edit_model(sim, 7.0)
    path = tmp_path / "quit.evx"
    monkeypatch.setattr("evans.ui.sim.sim_tab.QFileDialog.getSaveFileName",
                        lambda *a, **k: (str(path), ""))
    _answer(monkeypatch, sim, "save")
    assert win.confirm_quit()
    assert path.exists()
    assert not sim.is_unsaved()


def test_quit_save_then_cancelled_file_dialog_is_cancel(win, monkeypatch):
    sim = win._sim_tab
    _edit_model(sim)
    monkeypatch.setattr("evans.ui.sim.sim_tab.QFileDialog.getSaveFileName",
                        lambda *a, **k: ("", ""))
    _answer(monkeypatch, sim, "save")
    assert not win.confirm_quit()
    assert sim.is_unsaved()


def test_quit_cancel_on_the_live_script_keeps_evans_open(win, monkeypatch):
    live = win._console.live
    _edit_live(live)
    asked = _answer(monkeypatch, live, "cancel")
    model = _answer(monkeypatch, win._sim_tab)
    assert not win.confirm_quit()
    assert len(asked) == 1 and model == []       # stopped at the first


def test_quit_discard_on_the_live_script(win, monkeypatch):
    live = win._console.live
    _edit_live(live)
    _answer(monkeypatch, live, "discard")
    assert win.confirm_quit()


def test_quit_save_on_the_live_script(win, tmp_path, monkeypatch):
    live = win._console.live
    _edit_live(live)
    path = tmp_path / "quit.m"
    monkeypatch.setattr(live, "_ask_save_path", lambda *a: str(path))
    _answer(monkeypatch, live, "save")
    assert win.confirm_quit()
    assert path.exists()
    assert not live.is_unsaved()


def test_quit_live_save_then_cancelled_dialog_is_cancel(win, monkeypatch):
    live = win._console.live
    _edit_live(live)
    monkeypatch.setattr(live, "_ask_save_path", lambda *a: "")
    _answer(monkeypatch, live, "save")
    assert not win.confirm_quit()
    assert live.is_unsaved()


def test_quit_settles_both_in_turn(win, monkeypatch):
    _edit_live(win._console.live)
    _edit_model(win._sim_tab)
    live = _answer(monkeypatch, win._console.live, "discard")
    model = _answer(monkeypatch, win._sim_tab, "discard")
    assert win.confirm_quit()
    assert len(live) == len(model) == 1


# ── replacing the content ───────────────────────────────────────


def _example():
    from evans.examples import examples
    return examples()[0]


def test_example_over_an_unsaved_model(win, tmp_path, monkeypatch):
    sim = win._sim_tab
    example = _example()

    _edit_model(sim, 13.0)
    _answer(monkeypatch, sim, "cancel")
    assert not win.open_example(example)
    assert sim._t_end.value() == 13.0          # still the user's model

    _answer(monkeypatch, sim, "discard")
    assert win.open_example(example)
    assert not sim.is_unsaved()

    _edit_model(sim, 14.0)
    path = tmp_path / "mine.evx"
    monkeypatch.setattr("evans.ui.sim.sim_tab.QFileDialog.getSaveFileName",
                        lambda *a, **k: (str(path), ""))
    _answer(monkeypatch, sim, "save")
    assert win.open_example(example)
    assert path.exists()
    assert not sim.is_unsaved()


def test_opening_a_model_over_an_unsaved_one(win, tmp_path,
                                             monkeypatch):
    sim = win._sim_tab
    other = tmp_path / "other.evx"
    sim._canvas.root_model().save(other)
    monkeypatch.setattr("evans.ui.sim.sim_tab.QFileDialog.getOpenFileName",
                        lambda *a, **k: (str(other), ""))
    _edit_model(sim, 21.0)

    _answer(monkeypatch, sim, "cancel")
    sim.open_model()
    assert sim.model_path is None and sim.is_unsaved()

    _answer(monkeypatch, sim, "discard")
    sim.open_model()
    assert sim.model_path == other and not sim.is_unsaved()

    # Open Recent asks the same way.
    _edit_model(sim, 22.0)
    asked = _answer(monkeypatch, sim, "cancel")
    assert not win.open_recent(other)
    assert len(asked) == 1


def test_opening_a_live_script_over_an_unsaved_one(win, tmp_path,
                                                    monkeypatch):
    from evans.console.live import Cell, LiveDocument, save
    live = win._console.live
    other = save(LiveDocument([Cell.code("other = 1")]), tmp_path / "o.m")
    _edit_live(live, "mine = 1")

    _answer(monkeypatch, live, "cancel")
    assert not live.open(other)
    assert "mine = 1" in live._as_text()

    _answer(monkeypatch, live, "discard")
    assert live.open(other)
    assert "other = 1" in live._as_text() and not live.is_unsaved()

    _edit_live(live, "again = 1")
    _answer(monkeypatch, live, "save")
    assert live.open(other)                # saved over o.m, then reopened
    assert "again = 1" in live._as_text()
