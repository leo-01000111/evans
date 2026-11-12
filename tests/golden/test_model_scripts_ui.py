"""
Model scripts on the Model tab: open, Run, the trust prompt, the dialog.

The scripts run in a real console (a ``ConsoleWidget`` on an
``Interpreter``), so what they define is what the blocks read. The trust
prompt is answered by replacing ``SimTab._ask_trust``: a modal dialog no
test answers fails the suite (``tests/conftest.py``).
"""

from __future__ import annotations

import time

import pytest

pytest.importorskip("PySide6", reason="Qt not available")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from evans.console import Interpreter, matlab_runtime  # noqa: F401
from evans.sim.blocks import by_category  # noqa: F401  (registers library)
from evans.sim.model import SimModel
from evans.sim.scripts import BEFORE_RUN, ON_OPEN, ModelScript, path_key
from evans.ui import persist
from evans.ui.console.console_widget import ConsoleWidget
from evans.ui.sim.scripts_dialog import ModelScriptsDialog
from evans.ui.sim.sim_tab import SimTab


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def console(app):
    widget = ConsoleWidget(Interpreter())
    yield widget
    widget.deleteLater()


@pytest.fixture
def tab(app, console):
    widget = SimTab()
    widget.set_evaluator(console.interpreter.evaluate)
    widget.set_script_console(console)
    yield widget
    deadline = time.monotonic() + 10
    while widget._thread is not None and time.monotonic() < deadline:
        QApplication.processEvents()
    widget.deleteLater()


def answers(monkeypatch, tab, *replies):
    """Answer the trust prompt with ``replies`` in turn; returns the asks."""
    asked = []

    def ask(model, when):
        asked.append((model.name, when))
        return replies[len(asked) - 1]
    monkeypatch.setattr(tab, "_ask_trust", ask)
    return asked


def gain_model(name="m") -> SimModel:
    m = SimModel(name)
    m.add("Step", "r", step_time=0.0)
    m.add("Gain", "K", gain="Kp")
    m.add("TransferFcn", "G", num="1", den="1, 1")
    m.connect("r", "K")
    m.connect("K", "G")
    return m


def model_file(folder, scripts, name="m"):
    """A model file from someone else: its path is not trusted."""
    m = gain_model(name)
    m.scripts = scripts
    path = folder / f"{name}.evx"
    m.save(path)
    return path


def variable(console, name):
    return console.interpreter.namespace.get(name)


def transcript(console) -> str:
    return "\n".join(text for text, _kind in console._log)


# ── on open ─────────────────────────────────────────────────────

def test_a_trusted_model_runs_its_open_scripts_before_it_shows(
        tab, console, tmp_path, monkeypatch):
    (tmp_path / "setup.m").write_text("Kp = 7;\n", encoding="utf-8")
    path = model_file(tmp_path, [ModelScript("setup.m", on_open=True)])
    persist.trust_model(path)
    asked = answers(monkeypatch, tab)
    tab.load_model(path)
    assert asked == []
    assert variable(console, "Kp") == 7
    assert "Model script setup.m (on open)" in transcript(console)
    assert not tab._error_banner.has_error


def test_an_untrusted_model_asks_and_dont_run_skips(
        tab, console, tmp_path, monkeypatch):
    (tmp_path / "setup.m").write_text("Kp = 7;\n", encoding="utf-8")
    path = model_file(tmp_path, [ModelScript("setup.m", on_open=True)])
    asked = answers(monkeypatch, tab, "skip")
    tab.load_model(path)
    assert asked == [("m", ON_OPEN)]
    assert variable(console, "Kp") is None
    assert "did not run" in transcript(console)
    # The model opened all the same.
    assert tab._canvas.root_model().scripts == [
        ModelScript("setup.m", on_open=True)]


def test_run_this_time_is_asked_once_a_session(
        tab, console, tmp_path, monkeypatch):
    (tmp_path / "setup.m").write_text("n = exist('n', 'var') + 1;\n",
                                      encoding="utf-8")
    path = model_file(tmp_path, [ModelScript("setup.m", on_open=True)])
    asked = answers(monkeypatch, tab, "run")
    tab.load_model(path)
    tab.load_model(path)
    assert len(asked) == 1
    assert variable(console, "n") == 2
    assert path_key(path) not in persist.trusted_models()


def test_trust_this_model_is_remembered_across_sessions(
        app, console, tmp_path, monkeypatch):
    (tmp_path / "setup.m").write_text("Kp = 1;\n", encoding="utf-8")
    path = model_file(tmp_path, [ModelScript("setup.m", on_open=True)])
    first = SimTab()
    first.set_script_console(console)
    answers(monkeypatch, first, "trust")
    first.load_model(path)
    assert path_key(path) in persist.trusted_models()
    second = SimTab()
    second.set_script_console(console)
    asked = answers(monkeypatch, second)
    second.load_model(path)
    assert asked == []
    first.deleteLater()
    second.deleteLater()


def test_a_missing_open_script_warns_and_the_model_opens(
        tab, console, tmp_path):
    path = model_file(tmp_path, [ModelScript("nowhere/gone.m", on_open=True)])
    persist.trust_model(path)
    tab.load_model(path)
    assert "gone.m was not found" in transcript(console)
    assert tab.model_path == path
    assert not tab._error_banner.has_error


def test_a_failing_open_script_is_reported_and_the_model_opens(
        tab, console, tmp_path):
    (tmp_path / "bad.m").write_text("a = 1;\nb = not_defined;\n",
                                    encoding="utf-8")
    path = model_file(tmp_path, [ModelScript("bad.m", on_open=True)])
    persist.trust_model(path)
    tab.load_model(path)
    text = transcript(console)
    assert "not_defined" in text and "model script bad.m, line 2" in text
    assert tab.model_path == path


def test_saving_your_own_model_trusts_it_and_saving_a_strangers_does_not(
        tab, tmp_path, monkeypatch):
    tab._canvas.set_model(gain_model("mine"))
    tab._write_model(tmp_path / "mine.evx")
    assert path_key(tmp_path / "mine.evx") in persist.trusted_models()

    (tmp_path / "s.m").write_text("Kp = 1;\n", encoding="utf-8")
    theirs = model_file(tmp_path, [ModelScript("s.m", on_open=True)],
                        name="theirs")
    answers(monkeypatch, tab, "skip")
    tab.load_model(theirs)
    tab._write_model(tmp_path / "copy.evx")
    assert path_key(tmp_path / "copy.evx") not in persist.trusted_models()


# ── before a run ────────────────────────────────────────────────

def test_before_run_scripts_set_what_the_run_reads(tab, console, tmp_path):
    (tmp_path / "gains.m").write_text("Kp = 2.5;\n", encoding="utf-8")
    m = gain_model()
    m.scripts = [ModelScript(str(tmp_path / "gains.m"), before_run=True)]
    tab._canvas.set_model(m)
    tab.run_simulation()
    assert not tab._error_banner.has_error, tab._error_banner.message
    assert variable(console, "Kp") == 2.5
    assert tab._thread is not None                  # the run started


def test_a_failing_before_run_script_stops_the_run_and_names_it(
        tab, console, tmp_path):
    (tmp_path / "ok.m").write_text("Kp = 1;\n", encoding="utf-8")
    (tmp_path / "broken.m").write_text("x = 1;\ny = 1 + nope;\n",
                                       encoding="utf-8")
    m = gain_model()
    m.scripts = [ModelScript(str(tmp_path / "ok.m"), before_run=True),
                 ModelScript(str(tmp_path / "broken.m"), before_run=True)]
    tab._canvas.set_model(m)
    tab.run_simulation()
    assert tab._thread is None
    message = tab._error_banner.message
    assert "broken.m, line 2" in message and "nope" in message
    assert "… in model script broken.m, line 2" in transcript(console)


def test_an_untrusted_model_refused_before_a_run_stops_it(
        tab, console, tmp_path, monkeypatch):
    (tmp_path / "gains.m").write_text("Kp = 1;\n", encoding="utf-8")
    path = model_file(tmp_path, [ModelScript("gains.m", before_run=True)])
    asked = answers(monkeypatch, tab, "skip")
    tab.load_model(path)
    assert asked == []                    # nothing to run on open
    tab.run_simulation()
    assert asked == [("m", BEFORE_RUN)]
    assert tab._thread is None
    assert "not trusted" in tab._error_banner.message


# ── the dialog ──────────────────────────────────────────────────

def test_the_dialog_adds_orders_ticks_and_runs(app, tmp_path):
    for name in ("a.m", "b.m"):
        (tmp_path / name).write_text("", encoding="utf-8")
    (tmp_path / "lib").mkdir()
    (tmp_path / "lib" / "c.m").write_text("", encoding="utf-8")
    m = gain_model()
    m.save(tmp_path / "m.evx")
    m.scripts = [ModelScript("a.m", True, False)]
    ran = []
    dialog = ModelScriptsDialog(m, run_now=ran.append)
    dialog.add_files([tmp_path / "b.m", tmp_path / "lib" / "c.m",
                      tmp_path / "a.m"])           # a is listed already
    assert [s.path for s in dialog.scripts()] == ["a.m", "b.m", "lib/c.m"]
    assert dialog.scripts()[1] == ModelScript("b.m", True, True)

    dialog._table.selectRow(2)
    dialog.move_selected(-1)
    dialog.move_selected(-1)
    dialog.move_selected(-1)                       # already at the top
    assert [s.path for s in dialog.scripts()] == ["lib/c.m", "a.m", "b.m"]

    dialog._table.item(0, 1).setCheckState(Qt.Unchecked)   # c: not on open
    assert dialog.scripts()[0] == ModelScript("lib/c.m", False, True)

    dialog._table.selectRow(1)
    dialog.run_now()
    assert [[s.path for s in batch] for batch in ran] == [["a.m"]]
    dialog._table.clearSelection()
    dialog.run_now()
    assert [s.path for s in ran[1]] == ["lib/c.m", "a.m", "b.m"]

    dialog._table.selectRow(0)
    dialog.remove_selected()
    assert [s.path for s in dialog.scripts()] == ["a.m", "b.m"]
    # Nothing reached the model before OK.
    assert m.scripts == [ModelScript("a.m", True, False)]
    dialog.deleteLater()


def test_the_dialog_marks_a_missing_file(app, tmp_path):
    m = gain_model()
    m.save(tmp_path / "m.evx")
    m.scripts = [ModelScript("gone.m", True, True)]
    dialog = ModelScriptsDialog(m)
    assert "not found" in dialog._table.item(0, 0).text()
    assert not dialog.run_button.isEnabled()        # no runner given
    dialog.deleteLater()


def test_run_now_runs_in_the_console_without_asking(
        tab, console, tmp_path, monkeypatch):
    (tmp_path / "s.m").write_text("Kp = 9;\n", encoding="utf-8")
    path = model_file(tmp_path, [ModelScript("s.m")])   # ticked for neither
    asked = answers(monkeypatch, tab)
    tab.load_model(path)
    assert tab.run_scripts_now(tab._canvas.root_model().scripts) == 1
    assert asked == []
    assert variable(console, "Kp") == 9
