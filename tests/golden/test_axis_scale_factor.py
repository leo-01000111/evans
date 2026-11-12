"""
An axis without units puts a common factor ("×0.001") on its numbers only
when they are small (under 0.1) or large (over 1000). pyqtgraph's own rule
turned 0.3 into "300 ×0.001".
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="Qt not available")

from PySide6.QtWidgets import QApplication

from evans.ui import plots  # noqa: F401  (installs the rule)
from evans.ui.plots import make_plot


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def factor(app, top: float, units: str = "") -> float:
    widget = make_plot("t", "x", "y")
    plot = widget.getPlotItem()
    axis = plot.getAxis("left")
    axis.setLabel("y", units=units)
    plot.setYRange(0, top, padding=0)
    app.processEvents()
    axis.updateAutoSIPrefix()
    scale = axis.autoSIPrefixScale
    widget.deleteLater()
    return scale


@pytest.mark.parametrize("top", [0.3, 0.1, 1.0, 50.0, 1000.0])
def test_ordinary_numbers_keep_no_factor(app, top):
    assert factor(app, top) == 1.0


@pytest.mark.parametrize("top", [0.05, 0.002, 5000.0, 2e9])
def test_small_and_large_numbers_get_one(app, top):
    assert factor(app, top) != 1.0


def test_an_axis_with_units_keeps_its_prefixes(app):
    # 0.3 s reads as 300 ms, as before.
    assert factor(app, 0.3, units="s") != 1.0
