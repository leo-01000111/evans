"""
Renders a :class:`~evans.console.figures.FigureSpec` into a plot widget.

The console's API never touches Qt — it describes a figure and hands the
description to whatever sink is installed. This module is the sink the UI
installs, which is what keeps ``step(G)`` runnable from a headless script and
drawable in the window from the same code.

2-D axes are drawn with pyqtgraph (:class:`_Axes2D`), themed and fast, with
a hover readout and click-to-pin data tips (:class:`DataTips`). Axes that
need 3-D, and pie charts, are drawn by :mod:`evans.console.figure_mpl` on an
embedded matplotlib canvas in the theme's colours; mplot3d rotates them with
the mouse.

It is also where a figure leaves the application: :func:`export_figure`
writes one as PNG, SVG, PDF, EPS or CSV, choosing by the file's extension.
"""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path

import numpy as np
import pyqtgraph as pg
from pyqtgraph import PlotWidget, mkBrush, mkPen
from pyqtgraph.exporters import SVGExporter
from PySide6.QtCore import (
    QBuffer,
    QByteArray,
    QEventLoop,
    QIODevice,
    QObject,
    QPoint,
    QPointF,
    QRectF,
    Qt,
)
from PySide6.QtGui import (
    QAction,
    QColor,
    QImage,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPen,
    QPolygonF,
    QShortcut,
)
from PySide6.QtSvg import QSvgGenerator
from PySide6.QtWidgets import (
    QFileDialog,
    QGraphicsPathItem,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ...console import figure_mpl
from ...console.figures import FigureSpec, Trace
from .. import theme
from ..plots import (
    COLORS,
    add_hline,
    add_marker,
    add_text_annotation,
    add_vline,
    curve_pen,
    freq_vline,
    install_hover_readout,
    make_freq_plot,
    make_plot,
    plot_freq,
    role_colour,
    role_colours,
    set_title,
)


class FigureView(QWidget):
    """One figure: the widget a ``step`` or ``bode`` call produces."""

    def __init__(self, spec: FigureSpec, parent=None) -> None:
        super().__init__(parent)
        self.spec = spec
        #: Kept by the figure area: the number on the figure's tab, whether it
        #: has been written to disk, and whether a script run (rather than
        #: the prompt) drew it — a script's figures are its output, replaced
        #: by the next run, while a figure typed at the prompt is kept.
        self.number = 0
        self.saved = False
        self.from_script = False
        #: The data tips of each 2-D axes, and the matplotlib canvases.
        self.tips: list[DataTips] = []
        self.canvases: list = []
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        self._overlay: _AnnotationOverlay | None = None
        self._build()
        theme.notifier().changed.connect(self._on_theme)

    def _build(self) -> None:
        layout = self.layout()
        spec = self.spec
        builder = {
            "bode": self._bode,
            "nyquist": self._nyquist,
            "pzmap": self._pzmap,
            "rlocus": self._rlocus,
            "subplot": self._subplots,
            "pie": self._matplotlib,
        }.get(spec.kind, self._plain)
        if spec.kind == "xy" and (spec.is_3d or figure_mpl._view_3d(spec)):
            builder = self._matplotlib
        builder(layout)
        self._install_export_menu()
        if spec.extra.get("annotations"):
            self._overlay = _AnnotationOverlay(self, spec.extra["annotations"])

    def rebuild(self, spec: FigureSpec | None = None) -> None:
        """
        Draw the figure again from its spec — amended at the prompt, say —
        in place, keeping its tab, number and window.
        """
        self.spec = spec or self.spec
        self.saved = False
        _clear_layout(self.layout())
        if self._overlay is not None:
            self._overlay.setParent(None)
            self._overlay.deleteLater()
            self._overlay = None
        self.tips.clear()
        self.canvases.clear()
        self._build()

    def _on_theme(self, _tokens) -> None:
        # pyqtgraph plots re-theme themselves; a matplotlib canvas is redrawn.
        if self.canvases:
            self.rebuild()

    # ── export ──────────────────────────────────────────────────

    def plot_widgets(self) -> list[PlotWidget]:
        """The figure's plots, top to bottom — two for a Bode diagram."""
        return sorted(self.findChildren(PlotWidget),
                      key=lambda w: w.mapTo(self, QPoint(0, 0)).y())

    def collect_points(self, count: int | None) -> list[tuple[float, float, int]]:
        """
        ``ginput``: wait for clicks on the first plot, in data coordinates.

        Stops after ``count`` clicks, or when Return is pressed. The button
        is 1, 2 or 3 for the left, middle and right mouse button.
        """
        plots = self.plot_widgets()
        if not plots:
            return []
        plot = plots[0]
        points: list[tuple[float, float, int]] = []
        loop = QEventLoop()
        buttons = {Qt.LeftButton: 1, Qt.MiddleButton: 2, Qt.RightButton: 3}

        def clicked(event) -> None:
            at = plot.plotItem.vb.mapSceneToView(event.scenePos())
            points.append((float(at.x()), float(at.y()),
                           buttons.get(event.button(), 1)))
            event.accept()
            if count is not None and len(points) >= count:
                loop.quit()

        plot.scene().sigMouseClicked.connect(clicked)
        keys = [QShortcut(QKeySequence(k), self) for k in ("Return", "Enter")]
        for key in keys:
            key.setContext(Qt.WidgetWithChildrenShortcut)
            key.activated.connect(loop.quit)
        self.setFocus()
        try:
            if count is None or count > 0:
                loop.exec()
        finally:
            plot.scene().sigMouseClicked.disconnect(clicked)
            for key in keys:
                key.setParent(None)
        return points

    def drawn_with_matplotlib(self) -> bool:
        """Whether any of its axes is a matplotlib canvas (3-D, a pie)."""
        return any(isinstance(v, FigureView) and v.canvases
                   for v in [self, *self.findChildren(FigureView)])

    def _install_export_menu(self) -> None:
        """
        Put *Export figure* on the plot's own right-click menu.

        Added to pyqtgraph's view-box menu rather than replacing it, so
        right-click still offers the zoom and axis controls as well.
        """
        for widget in self.plot_widgets():
            menu = widget.getPlotItem().getViewBox().menu
            if menu is None or getattr(menu, "_evans_export", False):
                continue
            menu._evans_export = True
            menu.addSeparator()
            submenu = QMenu("Export figure", menu)
            for fmt, label in EXPORT_LABELS.items():
                action = QAction(label, submenu)
                action.triggered.connect(
                    lambda _checked=False, f=fmt: self.save_dialog(f))
                submenu.addAction(action)
            menu.addMenu(submenu)

    def save_dialog(self, fmt: str | None = None) -> Path | None:
        """
        Ask where to save the figure, then save it.

        ``fmt`` picks the filter the dialog starts on; the file's extension
        decides what is written. Returns the file written, or None.
        """
        start = fmt if fmt in EXPORT_FORMATS else "png"
        filters = ";;".join(EXPORT_FILTERS.values())
        path, chosen = QFileDialog.getSaveFileName(
            self, "Save figure", f"figure_{self.number or 1}.{start}",
            filters, EXPORT_FILTERS[start])
        if not path:
            return None
        path = Path(path)
        if path.suffix.lower().lstrip(".") not in EXPORT_FORMATS:
            # No extension typed: take the one the chosen filter names.
            picked = next((f for f, text in EXPORT_FILTERS.items()
                           if text == chosen), start)
            path = path.with_name(f"{path.name}.{picked}")
        try:
            export_figure(self, path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Save failed", str(exc))
            return None
        return path

    # ── kinds ───────────────────────────────────────────────────

    def _plain(self, layout) -> None:
        widget = make_plot(self.spec.title, self.spec.xlabel,
                           self.spec.ylabel)
        _Axes2D(self, widget).paint()
        layout.addWidget(widget)

    def _matplotlib(self, layout) -> None:
        """3-D axes or a pie: a matplotlib canvas, with a coordinate readout."""
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        from matplotlib.figure import Figure

        figure = Figure(figsize=(5, 4))
        canvas = FigureCanvasQTAgg(figure)
        axes = figure_mpl.draw(figure, self.spec, screen_look())
        self.canvases.append(canvas)
        readout = QLabel(" ")
        readout.setFont(theme.data_font(8.5))
        readout.setStyleSheet(f"color: {theme.tokens().ink_muted};")

        def moved(event) -> None:
            ax = event.inaxes
            if ax is None or ax not in axes:
                readout.setText(" ")
                return
            try:
                readout.setText(ax.format_coord(event.xdata, event.ydata))
            except (TypeError, ValueError):
                readout.setText(" ")

        canvas.mpl_connect("motion_notify_event", moved)
        if self.spec.is_3d:
            canvas.setToolTip("Drag to rotate; right-drag to zoom")
        layout.addWidget(canvas, 1)
        layout.addWidget(readout)

    def _subplots(self, layout) -> None:
        """``subplot``'s axes, each a figure of its own, on one grid."""
        panes = [p for p in self.spec.extra.get("panes", [])
                 if p["spec"] is not None]
        if self.spec.title:
            layout.addWidget(QLabel(self.spec.title, alignment=Qt.AlignCenter))
        grid = QGridLayout()
        shared_y = self.spec.extra.get("ylabel")
        if shared_y:                    # a tiled layout's ylabel(t, ...)
            row = QHBoxLayout()
            row.addWidget(_VerticalLabel(shared_y))
            row.addLayout(grid, 1)
            layout.addLayout(row, 1)
        else:
            layout.addLayout(grid, 1)
        # Panes from different m×n grids share the least common multiple.
        rows = math.lcm(*(p["rows"] for p in panes)) if panes else 1
        cols = math.lcm(*(p["cols"] for p in panes)) if panes else 1
        for pane in panes:
            m, n = pane["rows"], pane["cols"]
            cells = [c - 1 for c in pane["cells"]]
            r0, r1 = min(c // n for c in cells), max(c // n for c in cells)
            c0, c1 = min(c % n for c in cells), max(c % n for c in cells)
            grid.addWidget(FigureView(pane["spec"]), r0 * rows // m,
                           c0 * cols // n, (r1 - r0 + 1) * rows // m,
                           (c1 - c0 + 1) * cols // n)
        if self.spec.extra.get("xlabel"):
            layout.addWidget(QLabel(self.spec.extra["xlabel"],
                                    alignment=Qt.AlignCenter))

    def _bode(self, layout) -> None:
        """Magnitude over phase, sharing one frequency axis."""
        splitter = QSplitter(Qt.Vertical)
        magnitude = make_freq_plot("Bode — Magnitude", "|G| (dB)")
        phase = make_freq_plot("Bode — Phase", "Phase (°)")
        magnitude.setXLink(phase)
        splitter.addWidget(magnitude)
        splitter.addWidget(phase)
        layout.addWidget(splitter)

        mag_plot = magnitude.getPlotItem()
        mag_plot.addLegend(offset=(-10, 10))
        for i, trace in enumerate(self.spec.traces):
            plot_freq(mag_plot, trace.x, trace.y, pen=_pen(i, trace.style),
                      name=trace.label or None)
        add_hline(mag_plot, 0.0, role_colour("muted"), width=0.8)

        phase_plot = phase.getPlotItem()
        for i, (omega, degrees, _label) in enumerate(
                self.spec.extra.get("phase", [])):
            plot_freq(phase_plot, omega, degrees, pen=_pen(i, "line"))
        add_hline(phase_plot, -180.0, role_colour("muted"), width=0.8)

        # The margins are the reason anyone draws a Bode plot; mark them.
        for margins in self.spec.extra.get("margins", []):
            wc = margins.get("wc", float("nan"))
            w180 = margins.get("w180", float("nan"))
            if np.isfinite(wc):
                freq_vline(mag_plot, wc, color=role_colour("reference"),
                           label=f"ωc={wc:.3g}")
                freq_vline(phase_plot, wc, color=role_colour("reference"),
                           label=f"PM={margins.get('pm_deg', float('nan')):.1f}°")
            if np.isfinite(w180) and np.isfinite(margins.get("gm_dB",
                                                             float("inf"))):
                freq_vline(mag_plot, w180, color=role_colour("danger"),
                           label=f"GM={margins['gm_dB']:.2f} dB")

    def _nyquist(self, layout) -> None:
        widget = make_plot(self.spec.title, self.spec.xlabel,
                           self.spec.ylabel)
        plot = widget.getPlotItem()
        plot.setAspectLocked(True)
        plot.addLegend(offset=(-10, 10))
        for i, trace in enumerate(self.spec.traces):
            plot.plot(trace.x, trace.y, pen=_pen(i, trace.style),
                      name=trace.label or None)

        theta = np.linspace(0, 2 * np.pi, 200)
        plot.plot(np.cos(theta), np.sin(theta),
                  pen=_pen(5, "dashed"))
        add_marker(plot, -1.0, 0.0, symbol="x", color=role_colour("danger"), size=14)
        add_text_annotation(plot, -1.0, 0.06, "−1", role_colour("danger"))
        add_hline(plot, 0.0, role_colour("muted"), width=0.6)
        add_vline(plot, 0.0, role_colour("muted"), width=0.6)

        for counts in self.spec.extra.get("counts", []):
            verdict = ("closed loop stable" if counts["Z"] == 0
                       else f"{counts['Z']} unstable CL pole(s)")
            plot.setTitle(
                f"{self.spec.title} — N={counts['N']}, P={counts['P']}, "
                f"Z={counts['Z']} → {verdict}")
        layout.addWidget(widget)

    def _pzmap(self, layout) -> None:
        widget = make_plot(self.spec.title, self.spec.xlabel,
                           self.spec.ylabel)
        plot = widget.getPlotItem()
        plot.addLegend(offset=(-10, 10))
        for i, trace in enumerate(self.spec.traces):
            symbol = "x" if "pole" in trace.label else "o"
            plot.plot(trace.x, trace.y, pen=None, symbol=symbol,
                      symbolSize=13, symbolPen=curve_pen(i, 2.2),
                      name=trace.label or None)
        if self.spec.extra.get("discrete"):
            theta = np.linspace(0, 2 * np.pi, 200)
            plot.plot(np.cos(theta), np.sin(theta), pen=_pen(5, "dashed"))
            plot.setAspectLocked(True)
        add_hline(plot, 0.0, role_colour("muted"), width=0.6)
        add_vline(plot, 0.0, role_colour("muted"), width=0.6)
        _frame(plot, self.spec)
        _limits(plot, self.spec)
        layout.addWidget(widget)

    def _rlocus(self, layout) -> None:
        widget = make_plot(self.spec.title, self.spec.xlabel,
                           self.spec.ylabel)
        plot = widget.getPlotItem()
        for i, trace in enumerate(self.spec.traces):
            plot.plot(trace.x, trace.y, pen=_pen(i, "line"))
        add_hline(plot, 0.0, role_colour("muted"), width=0.6)
        add_vline(plot, 0.0, role_colour("muted"), width=0.6)

        marginal = self.spec.extra.get("K_marginal")
        if marginal is not None and np.isfinite(marginal):
            plot.setTitle(
                f"{self.spec.title} — crosses the imaginary axis at "
                f"K = {marginal:.4g}, ω = "
                f"{self.spec.extra.get('omega_marginal', float('nan')):.4g}")
        _frame(plot, self.spec)
        layout.addWidget(widget)




class _VerticalLabel(QWidget):
    """Text turned a quarter left, for a tiled layout's shared y label."""

    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text
        self.setFixedWidth(self.fontMetrics().height() + 6)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setPen(QColor(theme.tokens().ink))
        painter.translate(0, self.height())
        painter.rotate(-90)
        painter.drawText(QRectF(0, 0, self.height(), self.width()),
                         Qt.AlignCenter, self.text)
        painter.end()


# ──────────────────────────────────────────────────────────────
#  2-D axes
# ──────────────────────────────────────────────────────────────

_QT_STYLES = {"-": Qt.SolidLine, "--": Qt.DashLine, ":": Qt.DotLine,
              "-.": Qt.DashDotLine}
_SYMBOLS = {"o": "o", "s": "s", "d": "d", "^": "t1", "v": "t", "<": "t3",
            ">": "t2", "+": "+", "x": "x", "*": "star", ".": "o", "p": "p",
            "h": "h"}
#: Where ``legend(..., 'Location', loc)`` puts the box: pyqtgraph's offset
#: from the corner, negative from the right or bottom.
_LEGEND_OFFSETS = {"northeast": (-10, 10), "northwest": (10, 10),
                   "southeast": (-10, -10), "southwest": (10, -10),
                   "north": (-10, 10), "south": (-10, -10),
                   "east": (-10, 10), "west": (10, 10)}
#: Styles that are not a curve from zero: no zero line under them.
_FIELDS = {"image", "contour", "contourf", "fill", "quiver"}


def screen_look() -> figure_mpl.Look:
    """The theme's colours, for a figure matplotlib draws on screen."""
    t = theme.tokens()
    roles = role_colours(t)
    return figure_mpl.Look(background=t.surface, ink=t.ink,
                           muted=t.ink_muted, grid=t.rule,
                           reference=roles["reference"],
                           danger=roles["danger"], cycle=tuple(COLORS))


class _Polygon(QGraphicsPathItem):
    """
    A filled outline in data coordinates, as ``fill``, ``patch`` and
    ``contourf`` draw. Its data bounds, not its pen, size the view.
    """

    def __init__(self, path: QPainterPath, pen, brush) -> None:
        super().__init__(path)
        self.setPen(pen)
        self.setBrush(brush)
        rect = path.boundingRect()
        self._bounds = ((rect.left(), rect.right()),
                        (rect.top(), rect.bottom()))

    def dataBounds(self, axis, frac=1.0, orthoRange=None):
        return self._bounds[axis]


def _outline(x, y) -> QPainterPath:
    path = QPainterPath()
    path.addPolygon(QPolygonF([QPointF(float(a), float(b))
                               for a, b in zip(x, y)
                               if np.isfinite(a) and np.isfinite(b)]))
    path.closeSubpath()
    return path


class _Axes2D:
    """Draws one 2-D axes' spec on a pyqtgraph plot."""

    def __init__(self, view: FigureView, widget: PlotWidget) -> None:
        self.view = view
        self.widget = widget
        self.plot = widget.getPlotItem()
        self.spec = spec = view.spec
        self.extra = extra = spec.extra
        order = extra.get("colororder")
        self.cycle = list(order) if order else None
        self.n = 0
        cmap = extra.get("colormap")
        self.cmap = np.asarray(cmap if cmap is not None
                               else figure_mpl._viridis(), float)
        self.clim = figure_mpl.colour_limits(spec)
        self.logx = bool(extra.get("logx"))
        self.logy = bool(extra.get("logy"))
        self.right: pg.ViewBox | None = None
        self.legend = None
        self.mapped = False                 # something follows the colour map
        self.images: list[tuple] = []
        self.hover = install_hover_readout(self.plot, log_x=self.logx)
        self.quantity = "time" if spec.kind == "time" else "xy"

    # ── colours and pens ────────────────────────────────────────

    def colour(self, trace: Trace) -> str:
        colour = trace.props.get("color")
        if colour is None and self.extra.get("yyaxis"):
            cycle = self.cycle or COLORS
            return cycle[1 % len(cycle)] if trace.props.get("side") == \
                "right" else cycle[0]
        if colour in (None, "flat", "interp", "auto"):
            cycle = self.cycle or COLORS
            colour = cycle[self.n % len(cycle)]
            self.n += 1
        return self.ink(colour)

    @staticmethod
    def ink(colour: str) -> str:
        """Black, on the dark theme, is the theme's ink."""
        if colour == "#000000" and theme.tokens().is_night:
            return theme.tokens().ink
        return colour

    def pen(self, trace: Trace, colour: str, width: float = 2.0):
        p = trace.props
        style = p.get("linestyle", "--" if trace.style == "dashed" else "-")
        if style is None:
            return None
        if "linewidth" in p:
            width = max(p["linewidth"] * 1.3, 0.5)
        elif self.cycle is None and "color" not in p and not \
                self.extra.get("yyaxis"):
            # The theme's own colours: dashed once the five are used up.
            pen = curve_pen(self.n - 1, width)
            if style != "-":
                pen.setStyle(_QT_STYLES.get(style, Qt.SolidLine))
            return pen
        return mkPen(colour, width=width,
                     style=_QT_STYLES.get(style, Qt.SolidLine))

    def cmap_colour(self, value: float) -> QColor:
        lo, hi = self.clim
        t = 0.0 if hi == lo or not np.isfinite(value) else \
            min(max((value - lo) / (hi - lo), 0.0), 1.0)
        r, g, b = self.cmap[min(int(t * len(self.cmap)), len(self.cmap) - 1)]
        return QColor.fromRgbF(r, g, b)

    def _lut(self) -> np.ndarray:
        return (np.clip(self.cmap, 0, 1) * 255).astype(np.ubyte)

    # ── adding items ────────────────────────────────────────────

    def target(self, trace: Trace):
        if trace.props.get("side") == "right":
            return self.right_box()
        return self.plot

    def add(self, target, item, name: str = "", pen=None, brush=None) -> None:
        target.addItem(item)
        if name and self.legend is not None:
            if target is self.plot and hasattr(item, "implements") and                     item.implements("plotData"):
                pass                     # the plot lists it in the legend
            elif isinstance(item, (pg.PlotDataItem, pg.ScatterPlotItem)):
                self.legend.addItem(item, name)
            else:
                sample = pg.PlotDataItem([], [], pen=pen, fillLevel=0,
                                         fillBrush=brush)
                self.legend.addItem(sample, name)

    def right_box(self) -> pg.ViewBox:
        """``yyaxis right``'s view: its own y range, the left's x."""
        if self.right is None:
            plot = self.plot
            box = pg.ViewBox()
            plot.showAxis("right")
            plot.scene().addItem(box)
            # Above the plot, whose themed background would hide it.
            box.setZValue(plot.zValue() + 10)
            plot.getAxis("right").setGrid(False)
            plot.getAxis("right").linkToView(box)
            box.setXLink(plot)

            def follow() -> None:
                box.setGeometry(plot.vb.sceneBoundingRect())
                box.linkedViewChanged(plot.vb, box.XAxis)

            plot.vb.sigResized.connect(follow)
            follow()
            self.right = box
        return self.right

    # ── the whole axes ──────────────────────────────────────────

    def paint(self) -> None:
        plot, extra = self.plot, self.extra
        if extra.get("legend") != "off" and any(t.label
                                                for t in self.spec.traces):
            where = extra.get("legend_location", "northeast")
            self.legend = plot.addLegend(offset=_LEGEND_OFFSETS.get(
                where.replace("outside", ""), (-10, 10)))
        if extra.get("yyaxis"):
            self.right_box()
        for trace in self.spec.traces:
            getattr(self, "_" + trace.style, self._line)(self.target(trace),
                                                         trace)
        self._decorate()
        self.view.tips.append(DataTips(plot, self.hover, self.images))

    def _decorate(self) -> None:
        plot, extra, spec = self.plot, self.extra, self.spec
        if self.logx or self.logy:
            plot.setLogMode(x=self.logx, y=self.logy)
        elif spec.traces and not any(t.style in _FIELDS
                                     for t in spec.traces) \
                and not extra.get("axis_off"):
            add_hline(plot, 0.0, role_colour("muted"), width=0.6)
        if extra.get("subtitle"):
            set_title(plot, f"{spec.title}<br><span style='font-size:8pt'>"
                            f"{extra['subtitle']}</span>",
                      color=theme.tokens().ink)
        for entry in extra.get("texts", []):
            self._text(entry)
        for entry in extra.get("xlines", []):
            self._refline(entry, vertical=True)
        for entry in extra.get("ylines", []):
            self._refline(entry, vertical=False)
        if extra.get("grid") == "off" or any(t.style == "image"
                                             for t in spec.traces):
            plot.showGrid(x=False, y=False)    # no grid over a picture
        if extra.get("tight"):
            plot.getViewBox().setDefaultPadding(0.0)
        if extra.get("aspect") == "equal":
            plot.setAspectLocked(True)
        if extra.get("ydir") == "reverse":
            plot.invertY(True)
        if extra.get("axis_off"):
            plot.hideAxis("left")
            plot.hideAxis("bottom")
        right = extra.get("right", {})
        if self.right is not None:
            if right.get("ylabel"):
                plot.setLabel("right", right["ylabel"])
            if right.get("ylim") is not None:
                self.right.setYRange(*map(float, right["ylim"]), padding=0)
            else:
                self.right.enableAutoRange(axis=pg.ViewBox.YAxis)
            if not any(t.props.get("color") for t in spec.traces):
                cycle = self.cycle or COLORS
                for side, colour in (("left", cycle[0]),
                                     ("right", cycle[1 % len(cycle)])):
                    axis = plot.getAxis(side)
                    axis.setPen(colour)
                    axis.setTextPen(colour)
        _limits(plot, spec)
        if extra.get("colorbar") and self.mapped:
            self._colorbar(extra["colorbar"])

    def _colorbar(self, options: dict) -> None:
        colour_map = pg.ColorMap(np.linspace(0, 1, len(self.cmap)),
                                 self._lut())
        bar = pg.ColorBarItem(values=self.clim, colorMap=colour_map,
                              interactive=False, width=14,
                              label=options.get("label") or None,
                              colorMapMenu=False)
        bar.axis.setTextPen(theme.tokens().ink)
        self.plot.layout.addItem(bar, 2, 5)
        self.plot.layout.setColumnFixedWidth(4, 5)

    def _text(self, entry: dict) -> None:
        anchor = ({"left": 0.0, "center": 0.5, "right": 1.0}.get(
                      entry.get("halign", "left"), 0.0),
                  {"top": 0.0, "cap": 0.0, "middle": 0.5, "baseline": 0.8,
                   "bottom": 1.0}.get(entry.get("valign", "middle"), 0.5))
        item = pg.TextItem(entry["string"], color=self.ink(
            entry.get("color", theme.tokens().ink)), anchor=anchor,
            angle=entry.get("rotation", 0.0),
            fill=mkBrush(entry["background"]) if entry.get("background")
            not in (None, "none") else None)
        font = theme.data_font(entry.get("fontsize", 10) * 0.85)
        font.setBold(entry.get("fontweight") == "bold")
        item.setFont(font)
        item.setPos(entry["x"], entry["y"])
        self.plot.addItem(item)

    def _refline(self, entry: dict, vertical: bool) -> None:
        colour = self.ink(entry.get("color", theme.tokens().ink))
        style = _QT_STYLES.get(entry.get("linestyle", "-"), Qt.SolidLine)
        line = pg.InfiniteLine(
            pos=entry["value"], angle=90 if vertical else 0, movable=False,
            pen=mkPen(colour, width=entry.get("linewidth", 0.8) * 1.3,
                      style=style),
            label=entry.get("label") or None,
            labelOpts={"position": 0.92, "color": colour, "movable": False})
        self.plot.addItem(line)
        text = entry.get("label") or f"{'x' if vertical else 'y'} = " \
                                     f"{entry['value']:.4g}"
        if vertical:
            self.hover.model.add_mark(entry["value"], 0.0, text,
                                      kind="vline", colour=colour)
        else:
            self.hover.model.add_mark(0.0, entry["value"], text,
                                      kind="hline", colour=colour)

    # ── trace styles ────────────────────────────────────────────

    def _xy(self, trace: Trace):
        """The trace's points, without those a log axis cannot show."""
        x, y = trace.x, trace.y
        if self.logx or self.logy:
            keep = np.ones(len(x), bool)
            if self.logx:
                keep &= x > 0
            if self.logy:
                keep &= y > 0
            x, y = x[keep], y[keep]
        return x, y

    def _line(self, target, trace: Trace) -> None:
        colour = self.colour(trace)
        pen = self.pen(trace, colour)
        x, y = self._xy(trace)
        marker = trace.props.get("marker")
        kw = {}
        if marker:
            size = trace.props.get("markersize", 6.0) * 1.3
            kw.update(symbol=_SYMBOLS.get(marker, "o"),
                      symbolSize=size if marker != "." else size * 0.6,
                      symbolPen=mkPen(trace.props.get("markeredge") or colour,
                                      width=1.4),
                      symbolBrush=self._marker_brush(trace, colour))
        item = pg.PlotDataItem(x, y, pen=pen, name=trace.label or None, **kw)
        self.add(target, item, trace.label)
        if target is self.plot and not self.logy:
            self.hover.model.add_curve(x, y, quantity=self.quantity,
                                       name=trace.label, colour=colour,
                                       connected=pen is not None)

    _dashed = _line

    @staticmethod
    def _marker_brush(trace: Trace, colour: str):
        face = trace.props.get("markerface")
        if face not in (None, "none", "auto"):
            return mkBrush(face)
        if trace.props.get("marker") == "." or trace.props.get("filled"):
            return mkBrush(colour)
        return None

    def _scatter(self, target, trace: Trace) -> None:
        p = trace.props
        if not p and self.spec.kind != "xy":
            p = {"marker": "o"}
        colour = None if p.get("cdata") is not None or p.get("colors") \
            else self.colour(trace)
        x, y = self._xy(trace)
        n = len(x)
        sizes = np.sqrt(np.broadcast_to(np.asarray(p.get("sizes", 36.0),
                                                   float), (n,))) * 1.3 \
            if "sizes" in p else np.full(n, p.get("markersize", 6.0) * 1.3)
        if p.get("cdata") is not None:
            cdata = np.broadcast_to(np.asarray(p["cdata"], float), (n,))
            colours = [self.cmap_colour(v) for v in cdata]
            self.mapped = True
        elif p.get("colors"):
            colours = [QColor(c) for c in p["colors"]]
        else:
            colours = [QColor(colour)] * n
        marker = p.get("marker") or "o"
        filled = p.get("filled") or marker == "."
        item = pg.ScatterPlotItem(
            x=x, y=y, size=sizes, symbol=_SYMBOLS.get(marker, "o"),
            pen=[mkPen(c, width=p.get("linewidth", 1.0) * 1.3)
                 for c in colours],
            brush=[mkBrush(c) if filled else mkBrush(None) for c in colours],
            name=trace.label or None)
        self.add(target, item, trace.label)
        if target is self.plot and not self.logy:
            self.hover.model.add_curve(x, y, quantity=self.quantity,
                                       name=trace.label,
                                       colour=colour, connected=False)

    def _stem(self, target, trace: Trace) -> None:
        colour = self.colour(trace)
        x, y = trace.x, trace.y
        target.addItem(pg.PlotDataItem(
            np.repeat(x, 2), np.column_stack([np.zeros_like(y), y]).ravel(),
            pen=mkPen(colour, width=1.6), connect="pairs"))
        item = pg.PlotDataItem(x, y, pen=None, symbol="o", symbolSize=7,
                               symbolPen=mkPen(colour, width=1.4),
                               symbolBrush=None, name=trace.label or None)
        self.add(target, item, trace.label)
        self.hover.model.add_curve(x, y, quantity=self.quantity,
                                   name=trace.label, colour=colour,
                                   connected=False)

    def _bar(self, target, trace: Trace) -> None:
        colour = self.colour(trace)
        width = self.extra.get("bar_width", 0.8)
        base = trace.props.get("base")
        base = np.zeros_like(trace.y) if base is None else base
        pen = mkPen(theme.tokens().ink, width=0.6) \
            if theme.tokens().is_night is False else mkPen(colour, width=1.0)
        if trace.props.get("horizontal"):
            item = pg.BarGraphItem(y=trace.x, x0=base, width=trace.y - base,
                                   height=width, pen=pen, brush=colour)
        else:
            item = pg.BarGraphItem(x=trace.x, y0=base, height=trace.y - base,
                                   width=width, pen=pen, brush=colour)
        self.add(target, item, trace.label, pen=pen, brush=mkBrush(colour))
        x, y = (trace.y, trace.x) if trace.props.get("horizontal") else \
            (trace.x, trace.y)
        self.hover.model.add_curve(x, y, quantity=self.quantity,
                                   name=trace.label, colour=colour,
                                   connected=False)

    def _errorbar(self, target, trace: Trace) -> None:
        colour_before = self.n
        self._line(target, trace)
        p = trace.props
        colour = trace.props.get("color") or (
            (self.cycle or COLORS)[colour_before % len(self.cycle or COLORS)])
        x = trace.x
        spacing = np.diff(np.sort(x))
        spacing = spacing[spacing > 0]
        beam = 0.25 * float(spacing.min()) if spacing.size else 0.1
        kw = {k: np.asarray(p[key], float) for k, key in
              (("top", "ypos"), ("bottom", "yneg"), ("left", "xneg"),
               ("right", "xpos")) if p.get(key) is not None}
        target.addItem(pg.ErrorBarItem(x=x, y=trace.y, beam=beam,
                                       pen=mkPen(self.ink(colour), width=1.2),
                                       **kw))

    def _area(self, target, trace: Trace) -> None:
        colour = self.colour(trace)
        base = np.broadcast_to(np.asarray(trace.props.get("base", 0.0),
                                          float), trace.y.shape)
        upper = pg.PlotDataItem(trace.x, trace.y,
                                pen=mkPen(theme.tokens().ink, width=0.8))
        # FillBetweenItem fills between the curves' drawn paths, and a curve
        # with no pen has none: the floor is drawn, in a clear pen.
        lower = pg.PlotDataItem(trace.x, base, pen=mkPen(QColor(0, 0, 0, 0)))
        fill_colour = QColor(colour)
        fill_colour.setAlphaF(float(trace.props.get("alpha", 1.0)))
        brush = mkBrush(fill_colour)
        target.addItem(lower)
        target.addItem(upper)
        fill = pg.FillBetweenItem(upper, lower, brush=brush)
        fill.setZValue(upper.zValue() - 1)
        self.add(target, fill, trace.label, pen=mkPen(colour), brush=brush)
        self.hover.model.add_curve(trace.x, trace.y, quantity=self.quantity,
                                   name=trace.label, colour=colour)

    def _face_brush(self, trace: Trace):
        p = trace.props
        if p.get("cdata") is not None:
            self.mapped = True
            colour = self.cmap_colour(float(np.nanmean(p["cdata"])))
        elif p.get("color") == "none":
            return mkBrush(None)
        else:
            colour = QColor(self.ink(p["color"]) if p.get("color") not in (
                None, "flat", "interp") else self.colour(trace))
        colour.setAlphaF(float(p.get("alpha", 1.0)))
        return mkBrush(colour)

    def _fill(self, target, trace: Trace) -> None:
        edge = trace.props.get("edgecolor", "#000000")
        pen = mkPen(self.ink(edge), width=trace.props.get("linewidth", 0.5)
                    * 1.6) if edge != "none" else QPen(Qt.NoPen)
        brush = self._face_brush(trace)
        self.add(target, _Polygon(_outline(trace.x, trace.y), pen, brush),
                 trace.label, pen=pen, brush=brush)

    def _image(self, target, trace: Trace) -> None:
        C = np.asarray(trace.z, float)
        rows, cols = C.shape[:2]
        (x0, x1), (y0, y1) = trace.x[:2], trace.y[:2]
        dx = (x1 - x0) / (cols - 1) if cols > 1 else 1.0
        dy = (y1 - y0) / (rows - 1) if rows > 1 else 1.0
        if C.ndim == 3:                      # true colour: RGB in [0, 1]
            image = pg.ImageItem(np.clip(np.nan_to_num(C), 0, 1)
                                 .transpose(1, 0, 2), levels=(0.0, 1.0))
            image.setRect(QRectF(x0 - dx / 2, y0 - dy / 2, (x1 - x0) + dx,
                                 (y1 - y0) + dy))
            target.addItem(image)
            self.images.append((C, x0, dx, y0, dy))
            return
        if trace.props.get("direct"):
            levels = (1.0, float(len(self.cmap) + 1))
        else:
            levels = self.clim
            self.mapped = True
        shown = np.where(np.isfinite(C), C, levels[0])
        image = pg.ImageItem(shown.T)
        image.setLookupTable(self._lut())
        image.setLevels(levels)
        image.setRect(QRectF(x0 - dx / 2, y0 - dy / 2, (x1 - x0) + dx,
                             (y1 - y0) + dy))
        target.addItem(image)
        self.images.append((C, x0, dx, y0, dy))

    def _contour(self, target, trace: Trace) -> None:
        import contourpy
        p = trace.props
        gen = contourpy.contour_generator(trace.x, trace.y,
                                          np.ma.masked_invalid(trace.z))
        fixed = p.get("color") not in (None, "flat")
        width = p.get("linewidth", 0.5) * 2.0
        style = _QT_STYLES.get(p.get("linestyle", "-"), Qt.SolidLine)
        for level in np.asarray(p.get("levels", []), float):
            lines = gen.lines(float(level))
            if not lines:
                continue
            colour = QColor(self.ink(p["color"])) if fixed else \
                self.cmap_colour(level)
            xs = np.concatenate([np.append(seg[:, 0], np.nan) for seg in lines])
            ys = np.concatenate([np.append(seg[:, 1], np.nan) for seg in lines])
            target.addItem(pg.PlotDataItem(xs, ys, connect="finite",
                                           pen=mkPen(colour, width=width,
                                                     style=style)))
            self.hover.model.add_curve(xs, ys, quantity=self.quantity,
                                       name=f"level {level:.4g}",
                                       colour=colour.name())
            if p.get("showtext"):
                for seg in lines:
                    if len(seg) > 3:
                        x, y = seg[len(seg) // 2]
                        label = pg.TextItem(f"{level:.3g}", color=colour,
                                            anchor=(0.5, 0.5),
                                            fill=mkBrush(theme.tokens().surface))
                        label.setFont(theme.data_font(7.5))
                        label.setPos(x, y)
                        target.addItem(label)
        if not fixed:
            self.mapped = True

    def _contourf(self, target, trace: Trace) -> None:
        import contourpy
        p = trace.props
        lo, hi = p.get("zrange", (float(np.nanmin(trace.z)),
                                  float(np.nanmax(trace.z))))
        bounds = np.unique(np.concatenate(
            [[lo], np.asarray(p.get("levels", []), float), [hi]]))
        gen = contourpy.contour_generator(
            trace.x, trace.y, np.ma.masked_invalid(trace.z),
            fill_type=contourpy.FillType.OuterOffset)
        for a, b in zip(bounds[:-1], bounds[1:]):
            points, offsets = gen.filled(float(a), float(b))
            colour = self.cmap_colour((a + b) / 2)
            for pts, offs in zip(points, offsets):
                path = QPainterPath()
                path.setFillRule(Qt.OddEvenFill)
                for s, e in zip(offs[:-1], offs[1:]):
                    ring = pts[s:e]
                    path.addPolygon(QPolygonF([QPointF(float(x), float(y))
                                               for x, y in ring]))
                    path.closeSubpath()
                target.addItem(_Polygon(path, QPen(Qt.NoPen),
                                        mkBrush(colour)))
        self.mapped = True
        outline = Trace(trace.x, trace.y, "", "contour", trace.z,
                        {"levels": p.get("levels", []), "color": "#000000",
                         "linewidth": 0.4, "showtext": p.get("showtext")})
        self._contour(target, outline)
        self.mapped = True

    def _quiver(self, target, trace: Trace) -> None:
        colour = self.colour(trace)
        p = trace.props
        x, y, u, v = trace.x, trace.y, p["u"], p["v"]
        tx, ty = x + u, y + v
        alpha, beta = 0.33, 0.33
        segments_x = [x, tx,
                      tx, tx - alpha * (u + beta * v),
                      tx, tx - alpha * (u - beta * v)]
        segments_y = [y, ty,
                      ty, ty - alpha * (v - beta * u),
                      ty, ty - alpha * (v + beta * u)]
        xs = np.column_stack(segments_x).ravel()
        ys = np.column_stack(segments_y).ravel()
        item = pg.PlotDataItem(xs, ys, connect="pairs",
                               pen=self.pen(trace, colour, 1.4),
                               name=trace.label or None)
        self.add(target, item, trace.label)


# ──────────────────────────────────────────────────────────────
#  Data tips
# ──────────────────────────────────────────────────────────────

class DataTips(QObject):
    """
    MATLAB's data cursor on a 2-D plot: click a curve, a marker or an image
    and the hover readout stays pinned there; click a tip to take it off.
    Right-click offers *Remove data tips*. Hovering an image reads out the
    pixel under the cursor.
    """

    def __init__(self, plot, hover, images: list) -> None:
        super().__init__()
        self.plot = plot
        self.hover = hover
        self.images = images
        self.pinned: list[tuple] = []
        plot._data_tips = self               # lives as long as the plot
        scene = plot.scene()
        if scene is not None:
            scene.sigMouseClicked.connect(self._clicked)
            if images:
                scene.sigMouseMoved.connect(self._moved)
        menu = plot.getViewBox().menu
        if menu is not None:
            action = QAction("Remove data tips", menu)
            action.triggered.connect(self.clear)
            menu.addAction(action)

    def hit_at(self, vx: float, vy: float):
        """What a tip at view coordinates ``(vx, vy)`` would show, or None."""
        vb = self.plot.getViewBox()
        dx, dy = vb.viewPixelSize()
        hit = None
        if dx > 0 and dy > 0:
            hit = self.hover.model.hit(vx, vy, 1.0 / dx, 1.0 / dy)
        return hit or self._image_hit(vx, vy)

    def _image_hit(self, vx: float, vy: float):
        from ..plots import HoverHit
        for C, x0, dx, y0, dy in reversed(self.images):
            col = int(round((vx - x0) / dx)) if dx else 0
            row = int(round((vy - y0) / dy)) if dy else 0
            if 0 <= row < C.shape[0] and 0 <= col < C.shape[1]:
                px = C[row, col]
                value = (f"[{px[0]:.4g} {px[1]:.4g} {px[2]:.4g}]"
                         if np.ndim(px) else f"{px:.4g}")
                return HoverHit(
                    f"X = {col + 1}, Y = {row + 1}\nValue = {value}",
                    x0 + col * dx, y0 + row * dy, "curve", None)
        return None

    def _moved(self, pos) -> None:
        vb = self.plot.getViewBox()
        if not vb.sceneBoundingRect().contains(pos):
            return
        point = vb.mapSceneToView(pos)
        dx, dy = vb.viewPixelSize()
        if dx > 0 and dy > 0 and self.hover.model.hit(
                point.x(), point.y(), 1.0 / dx, 1.0 / dy) is not None:
            return
        hit = self._image_hit(point.x(), point.y())
        if hit is not None:
            self.hover.show_hit(hit)

    def _clicked(self, event) -> None:
        if event.button() != Qt.LeftButton or event.double():
            return
        pos = event.scenePos()
        vb = self.plot.getViewBox()
        if not vb.sceneBoundingRect().contains(pos):
            return
        for tip in self.pinned:
            if tip[1].sceneBoundingRect().contains(pos):
                self._remove(tip)
                return
        point = vb.mapSceneToView(pos)
        hit = self.hit_at(point.x(), point.y())
        if hit is not None:
            self.pin(hit)

    def pin(self, hit) -> None:
        """Leave a tip showing ``hit``, a :class:`~..plots.HoverHit`."""
        t = theme.tokens()
        colour = hit.colour or role_colour("highlight")
        marker = pg.ScatterPlotItem([hit.x], [hit.y], size=9, symbol="s",
                                    pen=mkPen(t.ink, width=1.2),
                                    brush=mkBrush(colour))
        label = pg.TextItem(hit.text, color=t.ink, anchor=(0, 1),
                            fill=mkBrush(t.surface),
                            border=mkPen(t.ink, width=1))
        label.setFont(theme.data_font(8.5))
        label.setPos(hit.x, hit.y)
        for item in (marker, label):
            item.setZValue(900)
            self.plot.addItem(item, ignoreBounds=True)
        self.pinned.append((marker, label, hit))

    def _remove(self, tip) -> None:
        for item in tip[:2]:
            self.plot.removeItem(item)
        self.pinned.remove(tip)

    def clear(self) -> None:
        for tip in list(self.pinned):
            self._remove(tip)


# ──────────────────────────────────────────────────────────────
#  Annotations, over the whole figure
# ──────────────────────────────────────────────────────────────

class _AnnotationOverlay(QWidget):
    """``annotation`` shapes, painted over the figure in its own fractions."""

    def __init__(self, view: FigureView, shapes: list[dict]) -> None:
        super().__init__(view)
        self.shapes = shapes
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setGeometry(view.rect())
        view.installEventFilter(self)
        self.raise_()
        self.show()

    def eventFilter(self, obj, event) -> bool:
        if event.type() == event.Type.Resize:
            self.setGeometry(obj.rect())
            self.raise_()
        return False

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        t = theme.tokens()

        def at(x, y) -> QPointF:
            return QPointF(x * w, (1 - y) * h)

        for a in self.shapes:
            colour = QColor(_Axes2D.ink(a.get("color") or t.ink))
            pen = QPen(colour, a.get("linewidth", 1.0) * 1.3)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            kind = a["type"]
            if kind in ("line", "arrow", "doublearrow", "textarrow"):
                (x0, x1), (y0, y1) = a["x"][:2], a["y"][:2]
                p0, p1 = at(x0, y0), at(x1, y1)
                painter.drawLine(p0, p1)
                if kind != "line":
                    _arrow_head(painter, p0, p1, colour)
                if kind == "doublearrow":
                    _arrow_head(painter, p1, p0, colour)
                if kind == "textarrow" and a.get("string"):
                    painter.setPen(colour)
                    painter.setFont(theme.data_font(9))
                    rect = QRectF(p0.x() - 160, p0.y() - 12, 156, 24) \
                        if x1 > x0 else QRectF(p0.x() + 4, p0.y() - 12, 160,
                                               24)
                    painter.drawText(rect, (Qt.AlignRight if x1 > x0 else
                                            Qt.AlignLeft) | Qt.AlignVCenter,
                                     a["string"])
                continue
            x, y, bw, bh = a["position"][:4]
            rect = QRectF(at(x, y + bh), at(x + bw, y))
            face = a.get("color") if kind != "textbox" else a.get("background")
            painter.setBrush(QColor(face) if face not in (None, "none")
                             else Qt.NoBrush)
            edge = a.get("edgecolor", a.get("color") or t.ink)
            painter.setPen(QPen(QColor(_Axes2D.ink(edge)), pen.widthF())
                           if edge != "none" else QPen(Qt.NoPen))
            if kind == "ellipse":
                painter.drawEllipse(rect)
            else:
                painter.drawRect(rect)
            if a.get("string"):
                painter.setPen(colour)
                painter.setFont(theme.data_font(a.get("fontsize", 10) * 0.85))
                painter.drawText(rect.adjusted(4, 2, -4, -2),
                                 Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap,
                                 a["string"])
        painter.end()


def _arrow_head(painter: QPainter, start: QPointF, tip: QPointF,
                colour: QColor) -> None:
    dx, dy = tip.x() - start.x(), tip.y() - start.y()
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    size = 9.0
    left = QPointF(tip.x() - size * ux + size * 0.45 * uy,
                   tip.y() - size * uy - size * 0.45 * ux)
    right = QPointF(tip.x() - size * ux - size * 0.45 * uy,
                    tip.y() - size * uy + size * 0.45 * ux)
    painter.save()
    painter.setBrush(colour)
    painter.setPen(Qt.NoPen)
    painter.drawPolygon(QPolygonF([tip, left, right]))
    painter.restore()


def _clear_layout(layout) -> None:
    """Empty a layout, detaching its widgets at once (deletion waits)."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.setParent(None)
            widget.deleteLater()
        elif item.layout() is not None:
            _clear_layout(item.layout())


def _limits(plot, spec: FigureSpec) -> None:
    """Axis limits a script set with ``axis``, ``xlim`` or ``ylim``."""
    xlim = spec.extra.get("xlim")
    ylim = spec.extra.get("ylim")
    if xlim is not None:
        plot.setXRange(float(xlim[0]), float(xlim[1]), padding=0)
    if ylim is not None:
        plot.setYRange(float(ylim[0]), float(ylim[1]), padding=0)


def _frame(plot, spec: FigureSpec) -> None:
    """
    Keep the imaginary axis from autoscaling to round-off.

    A set of real poles comes back from ``np.roots`` with imaginary parts
    around 1e-6; autoscaling to those makes coincident poles look spread out.
    """
    xs = np.concatenate([t.x for t in spec.traces]) if spec.traces else None
    ys = np.concatenate([t.y for t in spec.traces]) if spec.traces else None
    if xs is None or not len(xs):
        return
    x_lo, x_hi = float(np.min(xs)), float(np.max(xs))
    span = max(x_hi - x_lo, 1e-9)
    y_span = max(float(np.max(np.abs(ys))) if len(ys) else 0.0, 0.25 * span)
    plot.setXRange(x_lo - 0.15 * span, x_hi + 0.15 * span, padding=0)
    plot.setYRange(-y_span * 1.15, y_span * 1.15, padding=0)


def _pen(index: int, style: str):
    from PySide6.QtCore import Qt as _Qt

    pen = curve_pen(index, 2.0 if style == "line" else 1.4)
    if style == "dashed":
        pen.setStyle(_Qt.DashLine)
    return pen


# ──────────────────────────────────────────────────────────────
#  Export
# ──────────────────────────────────────────────────────────────

#: What a figure can be saved as, with the file dialog's filter for each.
EXPORT_FILTERS = {
    "png": "PNG image (*.png)",
    "svg": "SVG vector image (*.svg)",
    "pdf": "PDF document (*.pdf)",
    "eps": "EPS vector image (*.eps)",
    "jpg": "JPEG image (*.jpg)",
    "tif": "TIFF image (*.tif)",
    "csv": "CSV data (*.csv)",
}
EXPORT_FORMATS = tuple(EXPORT_FILTERS)
#: The plot menu's *Export figure* entries.
EXPORT_LABELS = {"png": "As PNG image…", "svg": "As SVG vector image…",
                 "pdf": "As PDF…", "eps": "As EPS…", "csv": "Data as CSV…"}
#: Other spellings of an extension, and the format each one is.
_ALIASES = {"jpeg": "jpg", "tiff": "tif"}
_PICTURES = {"png": "PNG", "jpg": "JPG", "tif": "TIFF"}


def export_figure(fig: FigureView, path: str | Path, *,
                  dpi: float | None = None) -> Path:
    """
    Write a figure to ``path``, in the format its extension names.

    ``.png``, ``.jpg`` and ``.tif`` are a picture of the figure as it is on
    screen, at ``dpi`` if given (the screen's 96 otherwise); ``.svg`` is the
    same as vector graphics (both plots of a Bode diagram, one above the
    other). ``.pdf`` and ``.eps`` are drawn again by matplotlib on a white
    page, for a paper (:func:`evans.console.figure_mpl.save`), as is an SVG
    of a figure with 3-D axes. ``.csv`` is the plotted data, an x and a y
    column per series.

    This is the one place a figure is written from, so the Save button, the
    plot's right-click menu and MATLAB's ``saveas``/``print`` all agree.
    Raises ``ValueError`` for an extension it does not know and ``OSError``
    when the file cannot be written. Marks the figure saved; returns the path.
    """
    path = Path(path)
    fmt = path.suffix.lower().lstrip(".")
    fmt = _ALIASES.get(fmt, fmt)
    if fmt not in EXPORT_FORMATS:
        raise ValueError(
            f"cannot save a figure as '{path.suffix or path.name}': use "
            + ", ".join(f".{f}" for f in EXPORT_FORMATS))
    if fmt in _PICTURES:
        if not _picture(fig, dpi).save(str(path), _PICTURES[fmt]):
            raise OSError(f"Qt could not write {path}")
    elif fmt in ("pdf", "eps") or (fmt == "svg"
                                   and fig.drawn_with_matplotlib()):
        figure_mpl.save(fig.spec, path, dpi=dpi)
    elif fmt == "svg":
        path.write_text(_figure_svg(fig), encoding="utf-8")
    else:
        _write_csv(fig.spec, path)
    fig.saved = True
    return path


def _picture(fig: FigureView, dpi: float | None) -> QImage:
    """The figure as on screen, scaled to ``dpi`` (96 is the screen's)."""
    if not dpi:
        return fig.grab().toImage()
    scale = max(float(dpi) / 96.0, 0.1)
    size = fig.size()
    image = QImage(max(int(size.width() * scale), 1),
                   max(int(size.height() * scale), 1), QImage.Format_ARGB32)
    image.fill(QColor(theme.tokens().surface))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.scale(scale, scale)
    fig.render(painter, QPoint(0, 0))
    painter.end()
    return image


def figure_series(spec: FigureSpec) -> list[tuple[str, np.ndarray]]:
    """
    The plotted data as named columns: an x and a y column per series.

    A Bode figure's phase curves are in ``spec.extra`` rather than in its
    traces; they are included, after the magnitudes.
    """
    bode = spec.kind == "bode"
    x_name = "w (rad/s)" if bode else (spec.xlabel or "x")
    y_name = "|G| (dB)" if bode else (spec.ylabel or "y")
    columns: list[tuple[str, np.ndarray]] = []
    if spec.kind == "subplot":
        for k, pane in enumerate(spec.extra.get("panes", [])):
            if pane["spec"] is not None:
                columns += [(f"axes {k + 1} {name}", values) for name, values
                            in figure_series(pane["spec"])]
        return columns
    for k, trace in enumerate(spec.traces):
        name = trace.label or f"series {k + 1}"
        columns.append((f"{name}: {x_name}",
                        np.asarray(trace.x, float).reshape(-1)))
        columns.append((f"{name}: {y_name}",
                        np.asarray(trace.y, float).reshape(-1)))
        if trace.z is not None:
            columns.append((f"{name}: {spec.extra.get('zlabel') or 'z'}",
                            np.asarray(trace.z, float).reshape(-1)))
    if bode:
        for k, (omega, degrees, label) in enumerate(
                spec.extra.get("phase", [])):
            name = label or f"series {k + 1}"
            columns.append((f"{name}: {x_name}", np.asarray(omega, float)))
            columns.append((f"{name}: phase (deg)",
                            np.asarray(degrees, float)))
    return columns


def _write_csv(spec: FigureSpec, path: Path) -> None:
    """Series of different lengths leave the shorter columns blank below."""
    columns = figure_series(spec)
    rows = max((len(values) for _name, values in columns), default=0)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([name for name, _values in columns])
        for i in range(rows):
            writer.writerow([repr(float(values[i])) if i < len(values) else ""
                             for _name, values in columns])


def _scene_svg(widget: PlotWidget) -> str:
    """
    One plot widget as SVG: pyqtgraph's exporter, which keeps the curves as
    editable paths, or Qt's own generator when the exporter cannot read
    what Qt wrote. PySide6 6.12 changed the path syntax QSvgGenerator emits,
    and pyqtgraph 0.14's post-processing fails on it with a ValueError.
    """
    try:
        return SVGExporter(widget.scene()).export(toBytes=True).decode("utf-8")
    except (ValueError, IndexError):
        pass
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.WriteOnly)
    generator = QSvgGenerator()
    generator.setOutputDevice(buffer)
    size = widget.size()
    generator.setSize(size)
    generator.setViewBox(QRectF(0, 0, size.width(), size.height()))
    painter = QPainter(generator)
    widget.render(painter)
    painter.end()
    buffer.close()
    return bytes(data).decode("utf-8")


def _figure_svg(fig: FigureView) -> str:
    """
    The figure as one SVG document.

    pyqtgraph exports one scene at a time, and a Bode figure is two plot
    widgets; each is exported and nested in an outer document, stacked as
    they are on screen.
    """
    parts = []
    width = height = 0.0
    for widget in fig.plot_widgets():
        text = _scene_svg(widget)
        text = re.sub(r"<\?xml[^>]*\?>", "", text, count=1).strip()
        box = re.search(r'viewBox\s*=\s*"([^"]+)"', text)
        w, h = ((float(v) for v in box.group(1).split()[2:4]) if box
                else (widget.width(), widget.height()))
        text = text.replace(
            "<svg", f'<svg x="0" y="{height:g}" width="{w:g}" '
                    f'height="{h:g}"', 1)
        parts.append(text)
        width, height = max(width, w), height + h
    return ('<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
            '<svg xmlns="http://www.w3.org/2000/svg" '
            'xmlns:xlink="http://www.w3.org/1999/xlink" version="1.2" '
            f'width="{width:g}" height="{height:g}" '
            f'viewBox="0 0 {width:g} {height:g}">\n'
            + "\n".join(parts) + "\n</svg>\n")
