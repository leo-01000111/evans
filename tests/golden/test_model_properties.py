"""
R6b: on the Model workspace a closed side panel is not lost.

Selecting exactly one block opens the panel on Properties (several blocks do
not, and neither does a rubber band passing through one), and while the panel
is closed a narrow vertical tab at the canvas's right edge brings it back.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="Qt not available")

from PySide6.QtCore import QRect, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from evans.sim import SimModel  # noqa: E402
from evans.ui.sim.arrange import INSET, TAB_LABEL  # noqa: E402
from evans.ui.sim.sim_tab import SimTab  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _model() -> SimModel:
    m = SimModel("pair")
    m.add("Step", "r", x=0, y=0)
    m.add("Gain", "K", x=200, y=0, gain=2.0)
    m.add("Scope", "out", x=400, y=0)
    return m


@pytest.fixture
def tab(app):
    widget = SimTab()
    widget.resize(1100, 700)
    widget._canvas.set_model(_model())
    widget.show()
    for _ in range(10):
        app.processEvents()
    yield widget
    widget.close_scope_windows()
    widget.shutdown()
    widget.deleteLater()


def _select(tab, *ids):
    """Select exactly ``ids`` as one gesture (one selection change)."""
    canvas = tab._canvas
    canvas._scene.blockSignals(True)
    canvas._scene.clearSelection()
    for block_id in ids:
        canvas._blocks[block_id].setSelected(True)
    canvas._scene.blockSignals(False)
    canvas._on_selection()


def test_one_selected_block_reopens_a_closed_panel_on_properties(tab):
    side = tab.side_panel
    side.add_tab("other", "Other")
    side.set_current("other")
    side.set_open(False)
    _select(tab, "K")
    assert side.is_open and side.current == "properties"


def test_an_open_panel_is_left_on_its_tab(tab):
    side = tab.side_panel
    side.add_tab("cedric", "Cedric")
    side.set_current("cedric")
    side.set_open(True)
    _select(tab, "K")
    assert side.is_open and side.current == "cedric"


def test_several_selected_blocks_leave_a_closed_panel_closed(tab):
    side = tab.side_panel
    side.set_open(False)
    _select(tab, "K", "out")
    assert not side.is_open
    _select(tab)                                   # nothing
    assert not side.is_open


def test_a_rubber_band_through_one_block_does_not_open_it(tab, monkeypatch):
    side = tab.side_panel
    side.set_open(False)
    monkeypatch.setattr(tab._canvas, "rubberBandRect",
                        lambda: QRect(0, 0, 40, 40))
    _select(tab, "K")
    assert not side.is_open


def test_the_vertical_tab_shows_only_while_the_panel_is_closed(tab, app):
    side, vtab = tab.side_panel, tab.properties_tab
    assert side.is_open and not vtab.isVisible()
    side.set_open(False)
    app.processEvents()
    assert vtab.isVisible()
    side.set_open(True)
    app.processEvents()
    assert not vtab.isVisible()


def test_the_vertical_tab_reads_properties_one_letter_per_line(tab):
    vtab = tab.properties_tab
    assert vtab.text() == TAB_LABEL
    assert vtab.text().replace("\n", "") == "\u2039PROPERTIES"
    assert all(len(line) == 1 for line in vtab.text().split("\n"))
    assert vtab.accessibleName() == "Show properties"
    assert vtab.width() < 40                       # narrow


def test_the_vertical_tab_opens_properties(tab, app):
    side, vtab = tab.side_panel, tab.properties_tab
    side.add_tab("other", "Other")
    side.set_current("other")
    side.set_open(False)
    app.processEvents()
    QTest.mouseClick(vtab, Qt.LeftButton)
    assert side.is_open and side.current == "properties"


def test_the_vertical_tab_sits_at_the_right_edge_under_the_arrange_panel(tab, app):
    tab.side_panel.set_open(False)
    app.processEvents()
    vtab, arrange = tab.properties_tab, tab._arrange
    vp = tab._canvas.viewport().geometry()
    assert vtab.y() >= arrange.y() + arrange.height() + INSET - 1
    assert vtab.geometry().right() >= vp.right() - 1
    assert not vtab.geometry().intersects(arrange.geometry())
    assert not vtab.geometry().intersects(tab.search_button.geometry())
