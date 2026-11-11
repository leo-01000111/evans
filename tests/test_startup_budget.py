"""
Startup-time budget: how long a cold process takes to import Evans, build the
main window and show it (offscreen). Run in a fresh subprocess so no import is
already warm. The point is to stop 1.x getting slowly heavier.

Measured 2026-11-11 on the development machine (Windows 11), five runs:
9.25, 9.09, 9.30, 9.51, 9.65 s, median 9.3 s. The default budget is 2x that,
20 s. A slower CI machine sets EVANS_STARTUP_BUDGET_S instead of skipping.
"""

import os
import subprocess
import sys

BUDGET_S = float(os.environ.get("EVANS_STARTUP_BUDGET_S", "20"))

SCRIPT = """
import time
t = time.perf_counter()
from PySide6.QtWidgets import QApplication
from evans.ui.mainwindow import MainWindow
app = QApplication([])
win = MainWindow()
win.show()
app.processEvents()
print(time.perf_counter() - t)
"""


def test_main_window_starts_within_budget():
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen",
               PYQTGRAPH_QT_LIB="PySide6")
    result = subprocess.run([sys.executable, "-c", SCRIPT], env=env,
                            capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stderr[-2000:]
    seconds = float(result.stdout.strip().splitlines()[-1])
    assert seconds < BUDGET_S, (
        f"startup took {seconds:.1f} s, over the {BUDGET_S:.0f} s budget "
        "(set EVANS_STARTUP_BUDGET_S on a slower machine)")
