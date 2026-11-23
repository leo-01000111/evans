"""
A running simulation must not freeze the window (R6d).

The solver is pure Python on a worker thread, so it competes with the UI
thread for the GIL. At the interpreter's default 5 ms switch interval the UI
thread was starved for seconds at a time; the Model tab shortens the interval
for the length of a run and puts it back after.
"""

from __future__ import annotations

import sys
import time

import pytest

pytest.importorskip("PySide6", reason="Qt not available")

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

import evans.ui.sim.sim_tab as sim_tab
from evans.ui.sim.sim_tab import RUN_SWITCH_INTERVAL, SimTab, course_loop


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def tab(app):
    widget = SimTab()
    yield widget
    widget.shutdown()
    widget.deleteLater()


def _busy_solver(seconds: float):
    """A stand-in for ``simulate``: pure-Python work for a while."""
    def run(model, progress=None, **options):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            sum(i * i for i in range(200))
        return object()
    return run


def _watch_until_done(tab) -> list[float]:
    """Spin the event loop until the run ends; the gaps between 10 ms beats."""
    gaps: list[float] = []
    last = [time.perf_counter()]

    def beat():
        now = time.perf_counter()
        gaps.append(now - last[0])
        last[0] = now

    loop = QEventLoop()
    heart = QTimer()
    heart.timeout.connect(beat)
    heart.start(10)
    done = QTimer()
    done.timeout.connect(lambda: loop.quit() if tab._thread is None else None)
    done.start(5)
    loop.exec()
    heart.stop()
    done.stop()
    return gaps


def test_the_ui_thread_keeps_getting_its_turn_during_a_run(tab):
    """The real solver on the course loop: at 5 ms the longest UI stall was
    over 2 s in a run of this length."""
    tab._canvas.set_model(course_loop())
    tab._solver.setCurrentText("ode45")
    tab._t_end.setValue(300)
    tab._step.setValue(0)
    tab.run_simulation()
    gaps = _watch_until_done(tab)
    assert len(gaps) > 100, "the UI thread hardly ran at all"
    assert max(gaps) < 0.5, f"the UI thread stalled for {max(gaps):.2f}s"


def test_the_switch_interval_is_shortened_for_a_run_and_restored(tab, monkeypatch):
    before = sys.getswitchinterval()
    seen = []
    solver = _busy_solver(0.3)

    def spy(model, progress=None, **options):
        seen.append(sys.getswitchinterval())
        return solver(model, progress, **options)

    monkeypatch.setattr(sim_tab, "simulate", spy)
    monkeypatch.setattr(tab, "_on_finished", lambda result: tab._teardown_thread())
    loop = QEventLoop()
    done = QTimer()
    done.timeout.connect(lambda: loop.quit() if tab._thread is None else None)
    done.start(5)
    tab.run_simulation()
    loop.exec()
    done.stop()
    assert seen == [RUN_SWITCH_INTERVAL]
    assert sys.getswitchinterval() == before
