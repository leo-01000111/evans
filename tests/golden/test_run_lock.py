"""
While a simulation runs, the model is read-only (R6d).

The run is held open by a stand-in ``simulate`` that waits on an event, so
the run stays active for exactly as long as a test needs it.
"""

from __future__ import annotations

import threading
import time

import pytest

pytest.importorskip("PySide6", reason="Qt not available")

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication, QGraphicsItem

import evans.ui.sim.sim_tab as sim_tab
from evans.console import Interpreter
from evans.sim import SimModel
from evans.ui.sim.canvas import LOCKED_MESSAGE
from evans.ui.sim.sim_tab import SimTab


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _loop() -> SimModel:
    m = SimModel("loop")
    m.add("Step", "r", x=0, y=0, step_time=0.0)
    m.add("Sum", "e", x=200, y=0, signs="+-")
    m.add("Gain", "K", x=400, y=0, gain=4.0)
    m.add("TransferFcn", "G", x=600, y=0, num="1", den="1, 1")
    m.connect("r", "e.in1")
    m.connect("e", "K")
    m.connect("K", "G")
    m.connect("G", "e.in2")
    return m


class _Hold:
    """A ``simulate`` that runs until released, honouring Stop."""

    def __init__(self) -> None:
        self.release = threading.Event()
        self.started = threading.Event()
        self.fail_with: str | None = None

    def __call__(self, model, progress=None, **options):
        self.started.set()
        while not self.release.is_set():
            progress(0.5)              # raises when Stop was pressed
            time.sleep(0.005)
        if self.fail_with:
            raise sim_tab.SimulationError(self.fail_with)
        return object()


@pytest.fixture
def running(app, monkeypatch):
    """(tab, interpreter, hold): a tab with a model, not yet running."""
    hold = _Hold()
    monkeypatch.setattr(sim_tab, "simulate", hold)
    it = Interpreter()
    tab = SimTab()
    tab.set_evaluator(it.evaluate)
    it.simulink = tab.bridge(lambda model: None)
    tab._canvas.set_model(_loop())
    tab.mark_saved()
    monkeypatch.setattr(tab, "_on_finished",
                        lambda result: tab._teardown_thread())
    yield tab, it, hold
    hold.release.set()
    tab.shutdown()
    tab.deleteLater()


def _start(app, tab, hold) -> None:
    tab.run_simulation()
    assert hold.started.wait(5)
    assert tab.running


def _until_idle(app, tab, seconds: float = 5.0) -> None:
    end = time.monotonic() + seconds
    while tab.running and time.monotonic() < end:
        app.processEvents()
        time.sleep(0.005)
    app.processEvents()


def _snapshot(tab):
    return tab._canvas.model.to_dict()


def test_edits_are_refused_while_running_and_allowed_after(app, running):
    tab, _it, hold = running
    canvas = tab._canvas
    messages: list[str] = []
    canvas.status.connect(messages.append)
    before = _snapshot(tab)

    _start(app, tab, hold)
    assert canvas.locked
    canvas.add_block("Gain", QPointF(0, 200))
    canvas.scene().clearSelection()
    canvas._blocks["K"].setSelected(True)
    canvas.delete_selection()
    canvas.paste()
    canvas._on_block_moved("K", 800.0, 800.0)
    tab._apply_params("K", {"gain": "9"})
    canvas.open_quick_insert(canvas.viewport().rect().center())
    assert _snapshot(tab) == before
    assert not canvas._blocks["K"].flags() & QGraphicsItem.ItemIsMovable
    assert messages and messages[-1] == LOCKED_MESSAGE
    assert not tab._inspector._apply.isEnabled()
    assert not tab._solver.isEnabled()

    hold.release.set()
    _until_idle(app, tab)
    assert not canvas.locked
    canvas._blocks["K"].setSelected(False)
    canvas.add_block("Gain", QPointF(0, 200))
    tab._apply_params("K", {"gain": "9"})
    assert _snapshot(tab) != before
    assert canvas._blocks["K"].flags() & QGraphicsItem.ItemIsMovable
    assert tab._solver.isEnabled()


def test_undo_and_redo_are_refused_while_running(app, running):
    tab, _it, hold = running
    canvas = tab._canvas
    canvas.add_block("Gain", QPointF(0, 200))
    edited = _snapshot(tab)
    canvas.undo_stack.undo()
    undone = _snapshot(tab)
    assert undone != edited

    _start(app, tab, hold)
    canvas.undo_stack.redo()
    assert _snapshot(tab) == undone
    hold.release.set()
    _until_idle(app, tab)
    canvas.undo_stack.redo()
    assert _snapshot(tab) == edited

    hold.release.clear()
    hold.started.clear()
    _start(app, tab, hold)
    canvas.undo_stack.undo()
    assert _snapshot(tab) == edited


def test_a_console_command_that_changes_the_model_is_refused(app, running):
    tab, it, hold = running
    _start(app, tab, hold)
    for line in ("set_param('loop/K', 'Gain', '12');",
                 "add_block('simulink/Math Operations/Gain', 'loop/K2');",
                 "delete_block('loop/K');",
                 "add_line('loop', 'r/1', 'K/1');",
                 "delete_line('loop', 'K/1', 'G/1');",
                 "sim('loop', 1);"):
        results = it.run_script(line, "matlab")
        assert any(getattr(r, "error", None) for r in results) or \
            any("simulation is running" in str(getattr(r, "text", ""))
                for r in results), line
    assert tab._canvas.model.block("K").params["gain"] == 4.0
    assert "K2" not in tab._canvas.model.blocks

    hold.release.set()
    _until_idle(app, tab)
    it.run_script("set_param('loop/K', 'Gain', '12');", "matlab")
    assert tab._canvas.model.block("K").params["gain"] in (12, 12.0, "12")


def test_stop_ends_the_run_and_lifts_the_lock(app, running):
    tab, _it, hold = running
    _start(app, tab, hold)
    assert tab._stop_btn.isEnabled() and not tab._run_btn.isEnabled()
    tab._stop_btn.click()
    _until_idle(app, tab)
    assert not tab.running
    assert not tab._canvas.locked
    assert tab._run_btn.isEnabled() and not tab._stop_btn.isEnabled()
    assert tab._inspector._read_only is False


def test_an_error_in_the_worker_lifts_the_lock(app, running, monkeypatch):
    tab, _it, hold = running
    hold.fail_with = "boom"
    reported = []
    monkeypatch.setattr(tab, "report_error",
                        lambda where, exc: reported.append(str(exc)))
    _start(app, tab, hold)
    hold.release.set()
    _until_idle(app, tab)
    assert reported == ["boom"]
    assert not tab._canvas.locked
    assert not tab.running


def test_closing_during_a_run_asks_and_stops_it(app, running, monkeypatch):
    tab, _it, hold = running
    _start(app, tab, hold)

    # Declined: the run goes on and the model stays.
    monkeypatch.setattr(tab, "_ask_stop_run", lambda: False)
    assert tab.settle_unsaved() is False
    tab.new_model()
    assert tab.running and tab._canvas.locked
    assert "K" in tab._canvas.model.blocks

    # Accepted: the run stops, the lock lifts, the model is replaced.
    monkeypatch.setattr(tab, "_ask_stop_run", lambda: True)
    tab.new_model()
    assert not tab.running and not tab._canvas.locked
    assert "K" not in tab._canvas.model.blocks
