"""
Scope: plot the signals a run recorded.

The last few runs are kept, so a change can be judged against what it
replaced: with "Compare" ticked, the same signals from earlier runs are drawn
under the new ones, dashed and fading with age. A model with an XY Graph
block can show that graph instead of the time plot. "Export…" writes the
run's signals to CSV or ``.mat``, or the plot to PNG, SVG, PDF or EPS (size,
DPI and theme chosen). Ctrl+C, or "Copy plot and data" in the right-click
menu, puts the plot as an image and the visible data as tab-separated text on
the clipboard.

The same widget is the Model tab's global scope (every logged signal) and
the plot in a Scope block's own window, which is given the signals wired
into that block and shows only those.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QMimeData, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .. import theme
from ..plots import add_hline, apply_theme, curve_pen, make_plot, role_colour

#: Above this many samples the display is decimated. The full data is kept for
#: export — only the drawing is thinned, because a pyqtgraph curve of a
#: million points makes panning unusable and shows nothing extra on screen.
MAX_DRAWN = 20_000
#: How many earlier runs are kept for comparison.
HISTORY = 5
#: The view choice that means "against time" rather than an XY graph.
TIME_VIEW = "Time"
#: Export extensions that draw the plot (through matplotlib) rather than
#: write the signals.
IMAGE_FORMATS = (".png", ".svg", ".pdf", ".eps")


class ScopeWidget(QWidget):
    """
    Multi-channel scope with a channel picker and a cursor readout.

    Signals are chosen by name (``block.port``), so the same widget shows a
    Scope block's channels or any other signal the run happened to log.
    ``signals`` limits it to those (a Scope block's window); ``None`` offers
    every logged signal and the XY Graph views (the global scope).
    """

    def __init__(self, parent=None, *, title: str = "Scope",
                 signals: list[str] | None = None) -> None:
        super().__init__(parent)
        self._result = None
        self._title = title
        self._only: list[str] | None = None
        self.set_signals(signals)
        #: Earlier runs, the most recent first.
        self.history: list = []
        self._checks: dict[str, QCheckBox] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(2, 2, 2, 2)

        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        self._view = QComboBox()
        self._view.addItem(TIME_VIEW)
        self._view.setVisible(self._only is None)
        self._view.setToolTip("Signals against time, or an XY Graph block's "
                              "y against x")
        self._view.currentTextChanged.connect(lambda _t: self._redraw())
        bar.addWidget(self._view)
        self._compare = QCheckBox("Compare with earlier runs")
        self._compare.setToolTip(
            "Draw the same signals from earlier runs, dashed, under this one")
        self._compare.toggled.connect(lambda _on: self._redraw())
        bar.addWidget(self._compare)
        self._depth = QSpinBox()
        self._depth.setRange(1, HISTORY)
        self._depth.setValue(2)
        self._depth.setSuffix(" runs")
        self._depth.setToolTip("How many earlier runs to draw")
        self._depth.valueChanged.connect(lambda _v: self._redraw())
        bar.addWidget(self._depth)
        bar.addStretch()
        self._export = QPushButton("Export…")
        self._export.setToolTip("Save the run's signals as CSV or .mat, or the "
                                "plot as PNG, SVG, PDF or EPS")
        self._export.clicked.connect(self._ask_export)
        self._export.setEnabled(False)
        bar.addWidget(self._export)
        root.addLayout(bar)

        self._plot = make_plot(self._title, "Time (s)", "Amplitude")
        self._plot.getPlotItem().addLegend(offset=(-10, 10))
        root.addWidget(self._plot, stretch=1)

        copy = QAction("Copy plot and data", self)
        copy.setShortcut(QKeySequence.Copy)
        copy.setShortcutContext(Qt.WidgetWithChildrenShortcut)
        copy.triggered.connect(self.copy_to_clipboard)
        self.addAction(copy)
        self._copy_action = copy
        self._plot.getPlotItem().vb.menu.addSeparator()
        self._plot.getPlotItem().vb.menu.addAction(copy)

        self._cursor = pg.InfiniteLine(angle=90, movable=True,
                                       pen=pg.mkPen(role_colour("reference"), width=1.2,
                                                    style=Qt.DashLine))
        self._cursor.sigPositionChanged.connect(self._update_readout)

        self._readout = QLabel("")
        self._readout.setTextFormat(Qt.PlainText)
        self._readout.setWordWrap(True)
        self._readout.setFont(theme.data_font(9))      # a readout is data
        root.addWidget(self._readout)

        picker = QScrollArea()
        picker.setWidgetResizable(True)
        picker.setMaximumHeight(96)
        self._picker_body = QWidget()
        self._picker_layout = QHBoxLayout(self._picker_body)
        self._picker_layout.setContentsMargins(4, 2, 4, 2)
        self._picker_layout.addStretch()
        picker.setWidget(self._picker_body)
        root.addWidget(picker)

    # ── data ────────────────────────────────────────────────────

    @property
    def result(self):
        """The run on show, or None."""
        return self._result

    def set_title(self, title: str) -> None:
        """The plot's title (a Scope block's, in its window)."""
        self._title = title
        self._redraw()

    def set_signals(self, signals: list[str] | None) -> None:
        """
        Show only ``signals`` (in that order, repeats dropped), or every
        logged one with ``None``. Takes effect on the next run shown.
        """
        self._only = None if signals is None else list(dict.fromkeys(signals))

    def _names(self, result) -> list[str]:
        """The signals offered in the picker for ``result``."""
        if self._only is None:
            return sorted(result.signals)
        return [n for n in self._only if n in result.signals]

    def show_result(self, result, preferred: list[str] | None = None) -> None:
        """
        Display a :class:`~evans.sim.solver.SimResult`.

        The channels ticked before stay ticked when the new run has them, so
        a parameter change can be watched on the same signals run after run.
        """
        previous = [n for n, c in self._checks.items() if c.isChecked()]
        if self._result is not None:
            self.history.insert(0, self._result)
            del self.history[HISTORY:]
        self._result = result
        for check in self._checks.values():
            check.setParent(None)
        self._checks.clear()

        names = self._names(result)
        if preferred is None:
            kept = [n for n in previous if n in names]
            if self._only is not None:
                preferred = kept or names
            else:
                preferred = kept or _default_channels(result, names)

        view = self._view.currentText()
        self._view.blockSignals(True)
        self._view.clear()
        self._view.addItem(TIME_VIEW)
        for title in (result.xy if self._only is None else ()):
            self._view.addItem(title)
        index = self._view.findText(view)
        self._view.setCurrentIndex(max(index, 0))
        self._view.blockSignals(False)
        self._export.setEnabled(True)

        for name in names:
            check = QCheckBox(result.label(name))
            check.setToolTip(name)
            check.setChecked(name in preferred)
            check.stateChanged.connect(self._redraw)
            self._picker_layout.insertWidget(
                self._picker_layout.count() - 1, check)
            self._checks[name] = check
        self._redraw()

    def _earlier(self) -> list:
        """The earlier runs to draw, the most recent first."""
        if not self._compare.isChecked():
            return []
        return self.history[:self._depth.value()]

    def _redraw(self) -> None:
        plot = self._plot.getPlotItem()
        plot.clear()
        view = self._view.currentText()
        if self._in_xy_view():
            self._draw_xy(plot, view)
            return
        apply_theme(plot, self._title, "Time (s)", "Amplitude")
        plot.addLegend(offset=(-10, 10))
        if self._result is None:
            return

        t = self._result.t
        stride = max(1, len(t) // MAX_DRAWN)
        drawn = 0
        for name, check in self._checks.items():
            if not check.isChecked():
                continue
            data = self._result.signals[name]
            for channel in range(data.shape[1]):
                shown = self._result.label(name)
                label = shown if data.shape[1] == 1 else f"{shown}[{channel}]"
                for age, old in enumerate(self._earlier(), start=1):
                    if name in old.signals and \
                            old.signals[name].shape[1] > channel:
                        ot = old.t
                        step = max(1, len(ot) // MAX_DRAWN)
                        plot.plot(ot[::step],
                                  old.signals[name][::step, channel],
                                  pen=_faded(drawn, age),
                                  name=f"{label} (run −{age})")
                plot.plot(t[::stride], data[::stride, channel],
                          pen=curve_pen(drawn, 1.9), name=label)
                drawn += 1

        if drawn:
            add_hline(plot, 0.0, role_colour("muted"), width=0.6)
            plot.addItem(self._cursor)
            self._cursor.setPos(float(t[len(t) // 2]) if len(t) else 0.0)
            self._update_readout()
        else:
            self._readout.setText("")

    def _draw_xy(self, plot, title: str) -> None:
        """An XY Graph block's y against x, with earlier runs' if asked."""
        x_name, y_name = self._result.xy[title]
        x_shown, y_shown = (self._result.label(x_name),
                            self._result.label(y_name))
        apply_theme(plot, title, x_shown, y_shown)
        plot.addLegend(offset=(-10, 10))
        for age, old in enumerate(self._earlier(), start=1):
            if x_name in old.signals and y_name in old.signals:
                plot.plot(old.signals[x_name][:, 0], old.signals[y_name][:, 0],
                          pen=_faded(0, age), name=f"run −{age}")
        plot.plot(self._result.signals[x_name][:, 0],
                  self._result.signals[y_name][:, 0],
                  pen=curve_pen(0, 1.9), name=f"{y_shown} vs {x_shown}")
        self._readout.setText("")

    def export(self, path, names: list[str] | None = None):
        """
        Write this run's signals to CSV or .mat: ``names``, else the ones
        this scope offers (all of them in the global scope).
        """
        from ...sim.export import export_signals
        if self._result is None:
            raise ValueError("there is no run to export yet")
        if names is None and self._only is not None:
            names = self._names(self._result)
        return export_signals(self._result, path, names)

    # ── copy and image export ───────────────────────────────────

    def _visible_range(self) -> tuple[tuple[float, float], tuple[float, float]]:
        (x0, x1), (y0, y1) = self._plot.getPlotItem().viewRange()
        return (float(x0), float(x1)), (float(y0), float(y1))

    def _shown_channels(self) -> list[tuple[int, str, str, int]]:
        """(colour index, signal, label, column) for each ticked channel."""
        out = []
        for name, check in self._checks.items():
            if not check.isChecked():
                continue
            width = self._result.signals[name].shape[1]
            shown = self._result.label(name)
            for channel in range(width):
                label = shown if width == 1 else f"{shown}[{channel}]"
                out.append((len(out), name, label, channel))
        return out

    def _in_xy_view(self) -> bool:
        return (self._result is not None and self._only is None
                and self._view.currentText() in self._result.xy)

    def data_text(self, visible_only: bool = True) -> str:
        """
        The plotted data as tab-separated text with a header row.

        Time view: ``t`` and one column per ticked channel, the samples inside
        the visible time range (all of them with ``visible_only=False``). XY
        view: the two signals. Full resolution, not the thinned drawing.
        """
        if self._result is None:
            return ""
        (x0, x1), _ = self._visible_range()
        if self._in_xy_view():
            x_name, y_name = self._result.xy[self._view.currentText()]
            xs = self._result.signals[x_name][:, 0]
            ys = self._result.signals[y_name][:, 0]
            rows = [("\t".join((self._result.label(x_name),
                                self._result.label(y_name))))]
            rows += [f"{a:.10g}\t{b:.10g}" for a, b in zip(xs, ys)]
            return "\n".join(rows)
        t = np.asarray(self._result.t, dtype=float)
        keep = (t >= x0) & (t <= x1) if visible_only else np.ones(len(t), bool)
        channels = self._shown_channels()
        columns = [t[keep]] + [self._result.signals[n][keep, c]
                               for _i, n, _l, c in channels]
        rows = ["\t".join(["t"] + [lab for _i, _n, lab, _c in channels])]
        for k in range(len(columns[0])):
            rows.append("\t".join(f"{col[k]:.10g}" for col in columns))
        return "\n".join(rows)

    def copy_to_clipboard(self) -> None:
        """Put the plot (image) and its visible data (text) on the clipboard."""
        if self._result is None:
            return
        mime = QMimeData()
        mime.setImageData(self._plot.grab().toImage())
        mime.setText(self.data_text())
        QApplication.clipboard().setMimeData(mime)

    def figure_spec(self, look=None):
        """
        What the plot shows, as a :class:`~evans.console.figures.FigureSpec`
        for matplotlib: the ticked channels (or the XY graph), earlier runs
        when "Compare" is on, over the range now in view.
        """
        from ...console.figures import FigureSpec
        if self._result is None:
            raise ValueError("there is no run to export yet")
        if look is None:
            look = _screen_look()
        cycle = look.cycle
        (x0, x1), (y0, y1) = self._visible_range()
        if self._in_xy_view():
            title = self._view.currentText()
            xn, yn = self._result.xy[title]
            xs, ys = self._result.label(xn), self._result.label(yn)
            spec = FigureSpec("xy", title, xs, ys)
            for age, old in enumerate(self._earlier(), start=1):
                if xn in old.signals and yn in old.signals:
                    spec.add(old.signals[xn][:, 0], old.signals[yn][:, 0],
                             f"run −{age}", color=cycle[0], linestyle="--",
                             alpha=max(0.15, 0.6 / age), linewidth=1.0)
            spec.add(self._result.signals[xn][:, 0],
                     self._result.signals[yn][:, 0], f"{ys} vs {xs}",
                     color=cycle[0])
        else:
            spec = FigureSpec("time", self._title, "Time (s)", "Amplitude")
            for i, name, label, channel in self._shown_channels():
                colour = cycle[i % len(cycle)]
                for age, old in enumerate(self._earlier(), start=1):
                    if name in old.signals and \
                            old.signals[name].shape[1] > channel:
                        spec.add(old.t, old.signals[name][:, channel],
                                 f"{label} (run −{age})", color=colour,
                                 linestyle="--", alpha=max(0.15, 0.6 / age),
                                 linewidth=1.0)
                spec.add(self._result.t, self._result.signals[name][:, channel],
                         label, color=colour)
        spec.extra["grid"] = True
        spec.extra["xlim"] = (x0, x1)
        spec.extra["ylim"] = (y0, y1)
        return spec

    def export_image(self, path, *, width: float = 6.4, height: float = 3.6,
                     dpi: float = 150, on_screen: bool = False) -> None:
        """
        Save the plot as PNG, SVG, PDF or EPS (by the extension) through the
        matplotlib path the console figures use. ``width`` and ``height`` are
        inches, so PNG pixels are size x ``dpi``. ``on_screen`` keeps the
        theme's colours; otherwise ink on a white page, for a paper.
        """
        from ...console import figure_mpl
        look = _screen_look() if on_screen else figure_mpl.PRINT
        figure_mpl.save(self.figure_spec(look), path, dpi=dpi, width=width,
                        height=height, look=look, tight=False)

    def _ask_export(self) -> None:
        if self._result is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export", "signals.csv",
            "CSV (*.csv);;MATLAB data (*.mat);;PNG image (*.png);;"
            "SVG image (*.svg);;PDF (*.pdf);;EPS (*.eps)")
        if not path:
            return
        if path.lower().endswith(IMAGE_FORMATS):
            options = _ImageOptions(self)
            if options.exec():
                self.export_image(path, **options.values())
        else:
            self.export(path)

    def _update_readout(self) -> None:
        if self._result is None or not len(self._result.t):
            return
        x = float(self._cursor.value())
        parts = [f"t = {x:.5g}"]
        for name, check in self._checks.items():
            if not check.isChecked():
                continue
            data = self._result.signals[name]
            for channel in range(data.shape[1]):
                value = float(np.interp(x, self._result.t, data[:, channel]))
                shown = self._result.label(name)
                label = shown if data.shape[1] == 1 else f"{shown}[{channel}]"
                parts.append(f"{label} = {value:.5g}")
        self._readout.setText("   ".join(parts))

    def clear(self) -> None:
        """Forget the run and the ones before it: a different model is open."""
        self._result = None
        self.history.clear()
        self._export.setEnabled(False)
        for check in self._checks.values():
            check.setParent(None)
        self._checks.clear()
        self._plot.getPlotItem().clear()
        self._readout.setText("")


def _screen_look():
    from ..console.figure_view import screen_look
    return screen_look()


class _ImageOptions(QDialog):
    """Size, resolution and theme for an exported image."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Export image")
        form = QFormLayout(self)
        self.width_in = QDoubleSpinBox()
        self.width_in.setRange(1.0, 40.0)
        self.width_in.setValue(6.4)
        self.width_in.setSuffix(" in")
        self.height_in = QDoubleSpinBox()
        self.height_in.setRange(1.0, 40.0)
        self.height_in.setValue(3.6)
        self.height_in.setSuffix(" in")
        self.dpi = QSpinBox()
        self.dpi.setRange(36, 1200)
        self.dpi.setValue(150)
        self.dpi.setToolTip("Pixels per inch (PNG); vector formats ignore it")
        self.theme = QComboBox()
        self.theme.addItems(["White page (for papers)", "As on screen"])
        form.addRow("Width", self.width_in)
        form.addRow("Height", self.height_in)
        form.addRow("Resolution", self.dpi)
        form.addRow("Theme", self.theme)
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def values(self) -> dict:
        return {"width": self.width_in.value(),
                "height": self.height_in.value(),
                "dpi": self.dpi.value(),
                "on_screen": self.theme.currentIndex() == 1}


def _faded(index: int, age: int):
    """An earlier run's pen: the channel's colour, dashed, fading with age."""
    pen = curve_pen(index, 1.4)
    colour = pen.color()
    colour.setAlphaF(max(0.15, 0.6 / age))
    pen.setColor(colour)
    pen.setStyle(Qt.DashLine)
    return pen


#: The course's own names for the reference and the plant output. A loop drawn
#: the way the lectures draw it has a source ``r`` and a plant ``G``, and the
#: first thing anyone wants to see is how well ``G`` follows ``r``.
REFERENCE_SIGNAL = "r.out"
PLANT_SIGNAL = "G.out"


def _default_channels(result, names: list[str]) -> list[str]:
    """
    What to show when a run finishes.

    The reference and the plant output (``r.out`` and ``G.out``) when the model
    has them: tracking is what a control loop is judged on, and the Scope
    block's own wiring often carries the controller effort instead, which
    dwarfs the response it is meant to explain. If only one of the two exists
    it is still shown alone.

    Otherwise, signals feeding a Scope block if there are any — that is what a
    Scope is for — and failing that the first few signals, so a model without
    a Scope still shows something rather than an empty plot.
    """
    tracking = [n for n in (REFERENCE_SIGNAL, PLANT_SIGNAL) if n in names]
    if tracking:
        return tracking
    wired = [s for sources in result.scopes.values() for s in sources]
    if wired:
        return [n for n in names if n in set(wired)]
    return names[:3]
