"""
Block shapes on the Model tab canvas (``ui/sim/shapes.py``).

A shape changes how a block's body is drawn and nothing else: the ports must
sit exactly where they did as plain boxes, in every orientation, because the
router and the port snapping read their positions. The tests also pin the
hit area, the "Classic block boxes" preference and the diagram exports.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionGraphicsItem

from evans.sim.model import SimModel
from evans.ui import persist, theme
from evans.ui.sim import shapes
from evans.ui.sim.canvas import SimCanvas
from evans.ui.sim.export import export_scene
from evans.ui.sim.items import BlockItem

SHAPED = sorted(shapes.SHAPES)
#: (rotation, flip): unturned, turned, mirrored, and both.
ORIENTATIONS = [(0, False), (90, False), (180, True), (270, True)]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def classic_off(app):
    shapes.set_classic(False)
    yield
    shapes.set_classic(False)


def _model() -> SimModel:
    model = SimModel("shapes")
    for i, type_name in enumerate(SHAPED):
        params = {"signs": "+-+"} if type_name == "Sum" else {}
        model.add(type_name, x=(i % 5) * 200, y=(i // 5) * 160, **params)
    model.add("TransferFcn", x=0, y=700)
    return model


def _item(type_name: str, rotation: int, flip: bool) -> BlockItem:
    model = SimModel("one")
    params = {"signs": "+-+"} if type_name == "Sum" else {}
    block = model.add(type_name, **params)
    return BlockItem(block, 0.0, 0.0, rotation, flip)


def _ports(item: BlockItem) -> dict:
    return {key: (round(p.pos().x(), 6), round(p.pos().y(), 6),
                  round(p.direction.x(), 6), round(p.direction.y(), 6))
            for key, p in item.ports.items()}


def test_every_requested_block_type_has_a_shape():
    assert set(SHAPED) == {
        "Gain", "Sum", "Product", "Integrator", "Saturation", "Switch",
        "Step", "Ramp", "Sine", "Mux", "Demux", "Goto", "From", "Inport",
        "Outport", "Subsystem"}


def test_an_unlisted_block_is_the_plain_box(classic_off):
    assert shapes.shape_for(_item("TransferFcn", 0, False).block) is shapes.RECT


@pytest.mark.parametrize("type_name", SHAPED)
@pytest.mark.parametrize("rotation,flip", ORIENTATIONS)
def test_ports_do_not_move_with_the_shape(app, type_name, rotation, flip):
    shapes.set_classic(True)
    try:
        boxed = _item(type_name, rotation, flip)
        boxed_ports, boxed_size = _ports(boxed), boxed.size()
        shapes.set_classic(False)
        shaped = _item(type_name, rotation, flip)
        assert _ports(shaped) == boxed_ports
        assert shaped.size() == boxed_size
        assert shapes.shape_for(shaped.block) is shapes.SHAPES[type_name]
    finally:
        shapes.set_classic(False)


@pytest.mark.parametrize("type_name", SHAPED)
@pytest.mark.parametrize("rotation,flip", ORIENTATIONS)
def test_the_hit_area_holds_the_body_and_stays_in_bounds(
        classic_off, type_name, rotation, flip):
    item = _item(type_name, rotation, flip)
    hit = item.shape()
    assert hit.contains(QPointF(0, 0))
    assert item.boundingRect().contains(hit.boundingRect())
    # A port is still the thing a click on it finds: its own hit area covers
    # its centre, and it is drawn above the block.
    for port in item.ports.values():
        assert port.shape().contains(QPointF(0, 0))
        assert port.zValue() > item.zValue()


def test_a_click_beside_a_triangle_misses_it(classic_off):
    item = _item("Gain", 0, False)
    rect = item.body_rect()
    corner = QPointF(rect.right() - 3, rect.top() + 3)
    assert not item.shape().contains(corner)
    shapes.set_classic(True)
    assert item.shape().contains(corner)


@pytest.mark.parametrize("type_name", SHAPED + ["TransferFcn"])
@pytest.mark.parametrize("rotation,flip", ORIENTATIONS)
@pytest.mark.parametrize("selected,night", [(False, False), (True, True)])
def test_every_shape_paints(classic_off, type_name, rotation, flip, selected,
                            night):
    theme.set_mode(theme.Mode.NIGHT if night else theme.Mode.DAY,
                   persist=False)
    try:
        item = _item(type_name, rotation, flip)
        item.set_error("broken" if selected else "")
        option = QStyleOptionGraphicsItem()
        if selected:
            option.state |= QStyle.State_Selected
        image = QImage(300, 300, QImage.Format_ARGB32)
        image.fill(0)
        painter = QPainter(image)
        painter.translate(150, 150)
        item.paint(painter, option)
        painter.end()
    finally:
        theme.set_mode(theme.Mode.DAY, persist=False)


def test_classic_boxes_toggles_and_persists(app):
    seen = []
    shapes.notifier().changed.connect(seen.append)
    try:
        shapes.set_classic(True)
        assert shapes.classic()
        assert persist.classic_block_boxes()
        shapes._classic = None                  # as on the next launch
        assert shapes.classic()
        assert shapes.shape_for(_item("Gain", 0, False).block) is shapes.RECT
        shapes.set_classic(False)
        shapes._classic = None
        assert not shapes.classic()
        assert not persist.classic_block_boxes()
        assert seen == [True, False]
    finally:
        shapes.notifier().changed.disconnect(seen.append)
        shapes.set_classic(False)


def test_classic_boxes_is_off_by_default(app):
    persist.settings().remove(persist.CLASSIC_BLOCK_BOXES_KEY)
    assert persist.classic_block_boxes() is False


@pytest.mark.parametrize("classic", [False, True])
@pytest.mark.parametrize("suffix", [".svg", ".pdf", ".png"])
def test_a_shaped_diagram_exports(app, tmp_path, classic, suffix):
    shapes.set_classic(classic)
    canvas = SimCanvas(_model())
    try:
        for i, item in enumerate(canvas._blocks.values()):
            item.rotation, item.flip = ORIENTATIONS[i % 4]
            item.refresh()
        out = export_scene(canvas._scene, tmp_path / f"shapes{suffix}")
        assert out.stat().st_size > 1000
    finally:
        canvas.deleteLater()
        shapes.set_classic(False)


def test_the_view_menu_switches_classic_boxes(app):
    from evans.ui.mainwindow import MainWindow
    win = MainWindow()
    try:
        action = win._act_classic_boxes
        assert not action.isChecked()
        action.trigger()
        assert shapes.classic() and persist.classic_block_boxes()
        action.trigger()
        assert not shapes.classic()
    finally:
        shapes.set_classic(False)
        win.close()
        win.deleteLater()
