"""
A running simulation must not freeze the window (R6d).

The solver is pure Python on a worker thread, so it competes with the UI
thread for the GIL. At the interpreter's default 5 ms switch interval the UI
thread was starved for seconds at a time; the Model tab shortens the interval
for the length of a run and puts it back after.

Only the setting is tested. A test of the stall itself was tried and removed
(2026-11-23): it did not fail without the fix on a 300 s run, and inside the
full suite the first heartbeat swallowed 13 to 18 s of work that earlier tests'
windows had left queued.
"""

from __future__ import annotations

import sys
import time

import pytest

pytest.importorskip("PySide6", reason="Qt not available")

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

import evans.ui.sim.sim_tab as sim_tab
from evans.ui.sim.sim_tab import RUN_SWITCH_INTERVAL, SimTab


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
