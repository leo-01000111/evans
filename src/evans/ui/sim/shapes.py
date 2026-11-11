"""
How a block's body looks on the canvas.
=======================================
:class:`~evans.ui.sim.items.BlockItem` owns a block's geometry (its size and
where its ports are) and hands the drawing to the :class:`Shape` chosen here by
block type. A shape only changes the body: the ports, the block's size and its
bounding box are the item's, so the router and the port snapping never see a
difference. Blocks with no shape of their own, and every block when the
"Classic block boxes" preference is on, use :data:`RECT`, the plain box.

Each shape works in the block's *unturned* frame: :data:`~.items.BLOCK_W`
wide, ``item.height()`` tall, inputs on the left edge and outputs on the
right. :func:`turn` maps that frame onto the item as it is rotated and
flipped, so a Gain's triangle points along the signal whichever way the block
faces. Text and the little plots of Step, Saturation and the like stay upright
and unmirrored: they are read, not routed.

A new block gets a shape by subclassing :class:`Shape` and adding it to
:data:`SHAPES`; nothing in ``BlockItem`` needs to change.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QLineF, QObject, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPainterPath,
    QPainterPathStroker,
    QPen,
    QPolygonF,
    QTransform,
)

from .. import persist, theme
from .items import (
    BLOCK_W,
    block_bg,
    block_border,
    block_text,
    error_colour,
    sel_colour,
)

#: How far the selection ring sits inside (or, on a thin shape, outside) the
#: outline, and how wide a wire lead counts as part of the block for a click.
RING_INSET = 4.0
LEAD_HIT = 8.0
#: Height of the block-id caption drawn under a shape that has no room for it.
CAPTION_H = 13.0


# ──────────────────────────────────────────────────────────────
#  The "Classic block boxes" preference
# ──────────────────────────────────────────────────────────────

class _Notifier(QObject):
    changed = Signal(bool)          # classic boxes on?


_notifier: _Notifier | None = None
_classic: bool | None = None


def notifier() -> _Notifier:
    """Emits ``changed`` when the classic-boxes preference is switched."""
    global _notifier
    if _notifier is None:
        _notifier = _Notifier()
    return _notifier


def classic() -> bool:
    """True when every block is drawn as the plain rectangle."""
    global _classic
    if _classic is None:
        _classic = persist.classic_block_boxes()
    return _classic


def set_classic(on: bool) -> None:
    """Switch the preference, remember it, and have the canvases repaint."""
    global _classic
    _classic = bool(on)
    persist.set_classic_block_boxes(_classic)
    notifier().changed.emit(_classic)


# ──────────────────────────────────────────────────────────────
#  Frame helpers
# ──────────────────────────────────────────────────────────────

def turn(item) -> QTransform:
    """The unturned frame → the item's, as ``BlockItem._turn`` does it."""
    t = QTransform()
    if item.flip:
        t = t * QTransform.fromScale(-1.0, 1.0)
    for _ in range(item.rotation // 90):
        t = t * QTransform(0, 1, -1, 0, 0, 0)      # (x, y) → (−y, x)
    return t


def port_ys(item, is_input: bool) -> list[float]:
    """The unturned y of each input (or output), as the item places them."""
    names = item.block.inputs if is_input else item.block.outputs
    h = item.height()
    return [item._port_y(i, len(names), h) for i in range(len(names))]


def _ring(path: QPainterPath) -> QPainterPath:
    """The selection ring: the outline drawn ``RING_INSET`` inside itself,
    or outside it when the shape is too thin to hold a ring."""
    stroker = QPainterPathStroker()
    stroker.setWidth(2 * RING_INSET)
    stroker.setJoinStyle(Qt.MiterJoin)
    band = stroker.createStroke(path)
    inner = path.subtracted(band)
    box = inner.boundingRect()
    if box.width() >= 8 and box.height() >= 8:
        return inner
    return path.united(band).simplified()


# ──────────────────────────────────────────────────────────────
#  Shapes
# ──────────────────────────────────────────────────────────────

class Shape:
    """
    The plain box, and the base every other shape builds on.

    Subclasses override :meth:`outline` (the body, unturned) and, as needed,
    :meth:`decorate` (what is drawn inside) and the class flags.
    """

    #: Draw a short wire from each port to the body, for a body that does not
    #: reach the block's edges (a circle, a bar).
    leads = False
    #: Where the block id goes: inside along the bottom, or under the shape.
    caption_inside = True
    #: Draw the block's text label in :meth:`label_rect`.
    show_label = True
    #: Line style of the outline.
    pen_style = Qt.SolidLine

    def outline(self, item) -> QPainterPath:
        """The body in the unturned frame."""
        h = item.height()
        path = QPainterPath()
        path.addRect(QRectF(-BLOCK_W / 2, -h / 2, BLOCK_W, h))
        return path

    def body(self, item) -> QPainterPath:
        """The body in the item's frame."""
        return turn(item).map(self.outline(item))

    def lead_lines(self, item) -> list[QLineF]:
        """Port-to-centre lines in the item's frame (hidden by the body)."""
        if not self.leads:
            return []
        t = turn(item)
        lines = []
        for is_input, x in ((True, -BLOCK_W / 2), (False, BLOCK_W / 2)):
            for y in port_ys(item, is_input):
                lines.append(t.map(QLineF(x, y, 0.0, y)))
        return lines

    def hit_area(self, item) -> QPainterPath:
        """What a click selects: the body, plus the leads to the ports."""
        path = self.body(item)
        lines = self.lead_lines(item)
        if lines:
            stroker = QPainterPathStroker()
            stroker.setWidth(LEAD_HIT)
            leads = QPainterPath()
            for line in lines:
                leads.moveTo(line.p1())
                leads.lineTo(line.p2())
            path = path.united(stroker.createStroke(leads))
        return path

    def label_rect(self, item) -> QRectF:
        """Where the label goes, in the item's frame (upright text)."""
        rect = item.body_rect()
        if self.caption_inside:
            return rect.adjusted(8, 4, -8, -16)
        return rect.adjusted(8, 4, -8, -4)

    def caption_rect(self, item, body: QPainterPath):
        """Where an outside caption goes: under the body, or beside the
        wire when the block is turned and its ports are top and bottom."""
        bottom = body.boundingRect().bottom() + 5      # clear of the shadow
        if item.rotation in (90, 270):
            return (QRectF(6, bottom, 60, CAPTION_H),
                    Qt.AlignLeft | Qt.AlignTop)
        rect = item.body_rect()
        return (QRectF(rect.left() - 20, bottom, rect.width() + 40, CAPTION_H),
                Qt.AlignHCenter | Qt.AlignTop)

    def fill(self, item) -> QColor:
        return block_bg()

    def decorate(self, painter: QPainter, item) -> None:
        """Draw inside the body; the label by default."""
        if self.show_label:
            painter.setPen(QPen(block_text()))
            item._draw_label(painter, self.label_rect(item))

    # ── the one paint routine every shape shares ──────────────

    def paint(self, painter: QPainter, item, selected: bool) -> None:
        body = self.body(item)
        border = error_colour() if item._error else block_border()
        rectangular = type(self) is Shape
        painter.setRenderHint(QPainter.Antialiasing, not rectangular)

        if selected and not item._error:
            # Lifted: the brand's hard offset slab, never a blur.
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(theme.tokens().shadow))
            painter.drawPath(body.translated(4, 4))

        lines = self.lead_lines(item)
        if lines:
            painter.setPen(QPen(border, 2.0, Qt.SolidLine, Qt.FlatCap))
            painter.drawLines(lines)

        painter.setPen(QPen(border, 2.0, self.pen_style, Qt.SquareCap,
                            Qt.MiterJoin))
        painter.setBrush(QBrush(self.fill(item)))
        painter.drawPath(body)
        self.decorate(painter, item)

        if selected:
            painter.setPen(QPen(sel_colour(), 3.0, Qt.SolidLine,
                                Qt.SquareCap, Qt.MiterJoin))
            painter.setBrush(Qt.NoBrush)
            if rectangular:
                painter.drawRect(item.body_rect().adjusted(4, 4, -4, -4))
            else:
                painter.drawPath(_ring(body))

        rect = item.body_rect()
        painter.setFont(theme.label_font(6.5))
        painter.setPen(QPen(theme.tokens().ink_muted))
        if self.caption_inside:
            painter.drawText(rect.adjusted(4, rect.height() - 16, -4, -2),
                             Qt.AlignCenter, item.block_id)
        else:
            where, flags = self.caption_rect(item, body)
            painter.drawText(where, flags, item.block_id)

        if item._error:
            box = body.boundingRect()
            # Over the box's corner; above a low shape, off its outline.
            top = box.top() - 2 if rectangular else                 max(box.top() - 18, rect.top() - 6)
            painter.setPen(QPen(error_colour(), 2.0))
            painter.setFont(theme.data_font(11, 700))
            painter.drawText(QRectF(box.right() - 16, top, 20, 18),
                             Qt.AlignCenter, "!")


#: The plain box: blocks without a shape, and every block in classic mode.
RECT = Shape()


def _symbol_pen() -> QPen:
    return QPen(block_text(), 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)


def _axis_pen() -> QPen:
    return QPen(QColor(theme.tokens().rule), 1.0)


def _plot_box(item) -> QRectF:
    """The area for a small upright plot, above the caption."""
    rect = item.body_rect().adjusted(14, 8, -14, -18)
    h = min(rect.height(), 30.0)
    w = min(rect.width(), h * 1.7)
    c = rect.center()
    return QRectF(c.x() - w / 2, c.y() - h / 2, w, h)


class GainShape(Shape):
    """A triangle pointing along the signal, the gain inside it."""

    caption_inside = False

    def outline(self, item):
        h = item.height()
        return _polygon([(-BLOCK_W / 2, -h / 2), (BLOCK_W / 2, 0.0),
                         (-BLOCK_W / 2, h / 2)])

    def label_rect(self, item):
        h = item.height()
        # The fat end of the triangle, where text fits.
        return turn(item).mapRect(QRectF(-BLOCK_W / 2 + 6, -h / 4,
                                         BLOCK_W * 0.55, h / 2))


class _RoundShape(Shape):
    """A circle (an ellipse on a tall block) wired to the ports by leads."""

    leads = True
    caption_inside = False

    def radii(self, item) -> tuple[float, float]:
        h = item.height()
        ry = h / 2 - 4
        return min(ry, BLOCK_W / 2 - 22), ry

    def outline(self, item):
        rx, ry = self.radii(item)
        path = QPainterPath()
        path.addEllipse(QPointF(0, 0), rx, ry)
        return path


class SumShape(_RoundShape):
    """A circle with each input's sign beside its port."""

    show_label = False

    def decorate(self, painter, item):
        signs = str(item.block.params.get("signs", ""))
        rx, ry = self.radii(item)
        t = turn(item)
        painter.setPen(QPen(block_text()))
        painter.setFont(theme.data_font(9, 700))
        for sign, y in zip(signs, port_ys(item, True)):
            edge = rx * math.sqrt(max(0.0, 1 - (y / ry) ** 2))
            # Outside the circle, on the side of the lead away from the
            # centre, so a sign never sits on a wire.
            at = t.map(QPointF(-edge - 10, y + (9.0 if y > 0 else -9.0)))
            painter.drawText(QRectF(at.x() - 7, at.y() - 7, 14, 14),
                             Qt.AlignCenter, "−" if sign == "-" else "+")


class ProductShape(_RoundShape):
    """A circle with × or ÷ in it."""

    show_label = False

    def decorate(self, painter, item):
        painter.setPen(QPen(block_text()))
        painter.setFont(theme.data_font(16, 600))
        rx, ry = self.radii(item)
        painter.drawText(QRectF(-rx, -ry, 2 * rx, 2 * ry), Qt.AlignCenter,
                         item.block.display_label())


class IntegratorShape(Shape):
    """A rounded box with 1/s set as a fraction."""

    show_label = False

    def outline(self, item):
        h = item.height()
        path = QPainterPath()
        path.addRoundedRect(QRectF(-BLOCK_W / 2, -h / 2, BLOCK_W, h), 12, 12)
        return path

    def decorate(self, painter, item):
        area = item.body_rect().adjusted(8, 4, -8, -14)
        c = area.center()
        painter.setPen(QPen(block_text()))
        painter.setFont(theme.data_font(11, 600))
        painter.drawText(QRectF(c.x() - 20, c.y() - 19, 40, 17),
                         Qt.AlignHCenter | Qt.AlignBottom, "1")
        painter.drawText(QRectF(c.x() - 20, c.y() + 2, 40, 17),
                         Qt.AlignHCenter | Qt.AlignTop, "s")
        painter.setPen(QPen(block_text(), 1.4))
        painter.drawLine(QPointF(c.x() - 10, c.y()), QPointF(c.x() + 10, c.y()))


class _PlotShape(Shape):
    """A box with a small upright plot of what the block does."""

    show_label = False

    def curve(self, box: QRectF) -> QPainterPath:
        raise NotImplementedError

    def axes(self, painter, box: QRectF) -> None:
        painter.setPen(_axis_pen())
        painter.drawLine(QPointF(box.left(), box.bottom()),
                         QPointF(box.right(), box.bottom()))
        painter.drawLine(QPointF(box.left(), box.top()),
                         QPointF(box.left(), box.bottom()))

    def decorate(self, painter, item):
        box = _plot_box(item)
        self.axes(painter, box)
        painter.setPen(_symbol_pen())
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(self.curve(box))


class StepShape(_PlotShape):
    def curve(self, box):
        x = box.left() + box.width() * 0.4
        return _path([(box.left(), box.bottom() - 2), (x, box.bottom() - 2),
                      (x, box.top() + 2), (box.right(), box.top() + 2)])


class RampShape(_PlotShape):
    def curve(self, box):
        x = box.left() + box.width() * 0.3
        return _path([(box.left(), box.bottom() - 2), (x, box.bottom() - 2),
                      (box.right(), box.top() + 2)])


class SineShape(_PlotShape):
    def axes(self, painter, box):
        painter.setPen(_axis_pen())
        mid = box.center().y()
        painter.drawLine(QPointF(box.left(), mid), QPointF(box.right(), mid))
        painter.drawLine(QPointF(box.left(), box.top()),
                         QPointF(box.left(), box.bottom()))

    def curve(self, box):
        amp, mid = box.height() / 2 - 2, box.center().y()
        return _path([(box.left() + box.width() * i / 40,
                       mid - amp * math.sin(2 * math.pi * i / 40 * 1.5))
                      for i in range(41)])


class SaturationShape(_PlotShape):
    """Flat, slope, flat: the characteristic through the origin."""

    def axes(self, painter, box):
        painter.setPen(_axis_pen())
        c = box.center()
        painter.drawLine(QPointF(box.left(), c.y()), QPointF(box.right(), c.y()))
        painter.drawLine(QPointF(c.x(), box.top()), QPointF(c.x(), box.bottom()))

    def curve(self, box):
        c, dx = box.center(), box.width() * 0.22
        top, bottom = box.top() + 2, box.bottom() - 2
        return _path([(box.left(), bottom), (c.x() - dx, bottom),
                      (c.x() + dx, top), (box.right(), top)])


class SwitchShape(Shape):
    """Two contacts, a lever to the output, the control input between them.
    Drawn in the unturned frame, so the contacts face the input ports."""

    show_label = False
    caption_inside = False

    def decorate(self, painter, item):
        ys = port_ys(item, True)
        if len(ys) != 3:
            return Shape.decorate(self, painter, item)
        t = turn(item)
        left, contact, pivot = -BLOCK_W / 2 + 6, -16.0, 22.0
        pen = _symbol_pen()
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        for y in (ys[0], ys[2]):
            painter.drawLine(t.map(QLineF(left, y, contact, y)))
        painter.drawLine(t.map(QLineF(pivot, 0, BLOCK_W / 2 - 6, 0)))
        painter.drawLine(t.map(QLineF(pivot, 0, contact + 2, ys[0] + 5)))
        dashed = QPen(QColor(theme.tokens().ink_muted), 1.2, Qt.DashLine)
        painter.setPen(dashed)
        painter.drawLine(t.map(QLineF(left, 0, 2, 0)))
        painter.setPen(pen)
        painter.setBrush(QBrush(block_text()))
        for x, y in ((contact, ys[0]), (contact, ys[2]), (pivot, 0)):
            painter.drawEllipse(t.map(QPointF(x, y)), 2.6, 2.6)


class BarShape(Shape):
    """Mux and Demux: a narrow solid bar, wired to the ports by leads."""

    leads = True
    caption_inside = False
    show_label = False
    WIDTH = 10.0

    def outline(self, item):
        h = item.height()
        path = QPainterPath()
        path.addRect(QRectF(-self.WIDTH / 2, -h / 2 + 4, self.WIDTH, h - 8))
        return path

    def fill(self, item):
        return block_border()


class _TagShape(Shape):
    """A low tag across the block's middle, its text inside."""

    caption_inside = False
    HALF = 17.0

    def label_rect(self, item):
        return turn(item).mapRect(QRectF(-BLOCK_W / 2 + 10, -self.HALF,
                                         BLOCK_W - 20, 2 * self.HALF))


class GotoShape(_TagShape):
    """A flag pointing away along the signal: the value leaves here."""

    def outline(self, item):
        w, s = BLOCK_W / 2, self.HALF
        return _polygon([(-w, -s), (w - s, -s), (w, 0.0), (w - s, s), (-w, s)])


class FromShape(_TagShape):
    """A flag with a notched tail: the value arrives from a Goto."""

    def outline(self, item):
        w, s = BLOCK_W / 2, self.HALF
        return _polygon([(-w, -s), (w, -s), (w, s), (-w, s), (-w + s, 0.0)])


class PortShape(_TagShape):
    """Inport and Outport: a pill."""

    def outline(self, item):
        s = self.HALF
        path = QPainterPath()
        path.addRoundedRect(QRectF(-BLOCK_W / 2, -s, BLOCK_W, 2 * s), s, s)
        return path


class SubsystemShape(Shape):
    """
    A box with a location-plate band across the top carrying the name.

    The band and the outline are attributes, so a variant (a linked
    subsystem, say) is a one-line subclass or instance:
    ``SubsystemShape(dashed=True)``.
    """

    BAND = 17.0

    def __init__(self, dashed: bool = False, band: str = "plate",
                 band_text: str = "on_plate") -> None:
        self.pen_style = Qt.DashLine if dashed else Qt.SolidLine
        self.band, self.band_text = band, band_text

    def decorate(self, painter, item):
        rect = item.body_rect()
        band = QRectF(rect.left(), rect.top(), rect.width(), self.BAND)
        tokens = theme.tokens()
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(getattr(tokens, self.band)))
        painter.drawRect(band.adjusted(1, 1, -1, 0))
        head, _, rest = item.block.display_label().partition("\n")
        painter.setPen(QPen(QColor(getattr(tokens, self.band_text))))
        painter.setFont(theme.sign_font(8))
        painter.drawText(band.adjusted(6, 0, -6, 0),
                         Qt.AlignCenter | Qt.TextSingleLine,
                         painter.fontMetrics().elidedText(
                             head, Qt.ElideRight, int(band.width() - 12)))
        painter.setPen(QPen(block_text()))
        painter.setFont(theme.data_font(7))
        painter.drawText(rect.adjusted(6, self.BAND + 2, -6, -16),
                         Qt.AlignCenter | Qt.TextWordWrap, rest)


def _polygon(points) -> QPainterPath:
    path = QPainterPath()
    path.addPolygon(QPolygonF([QPointF(x, y) for x, y in points]))
    path.closeSubpath()
    return path


def _path(points) -> QPainterPath:
    path = QPainterPath(QPointF(*points[0]))
    for x, y in points[1:]:
        path.lineTo(x, y)
    return path


_ROUND_TAG = PortShape()

#: Block type → its shape. A type not listed here is drawn as :data:`RECT`.
SHAPES: dict[str, Shape] = {
    "Gain": GainShape(),
    "Sum": SumShape(),
    "Product": ProductShape(),
    "Integrator": IntegratorShape(),
    "Saturation": SaturationShape(),
    "Switch": SwitchShape(),
    "Step": StepShape(),
    "Ramp": RampShape(),
    "Sine": SineShape(),
    "Mux": BarShape(),
    "Demux": BarShape(),
    "Goto": GotoShape(),
    "From": FromShape(),
    "Inport": _ROUND_TAG,
    "Outport": _ROUND_TAG,
    "Subsystem": SubsystemShape(),
}


def shape_for(block) -> Shape:
    """The shape to draw ``block`` with, honouring the classic preference."""
    if classic():
        return RECT
    return SHAPES.get(block.type_name, RECT)
