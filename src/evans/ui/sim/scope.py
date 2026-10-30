"""
Scope: plot the signals a run recorded.

The last few runs are kept, so a change can be judged against what it
replaced: with "Compare" ticked, the same signals from earlier runs are drawn
under the new ones, dashed and fading with age. A model with an XY Graph
block can show that graph instead of the time plot. "Export…" writes the
run's signals to CSV or ``.mat``.
"""

from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
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


class ScopeWidget(QWidget):
    """
    Multi-channel scope with a channel picker and a cursor readout.

    Signals are chosen by name (``block.port``), so the same widget shows a
    Scope block's channels or any other signal the run happened to log.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._result = None
        #: Earlier runs, the most recent first.
        self.history: list = []
        self._checks: dict[str, QCheckBox] = {}

        root = QVBoxLayout(self)
        root.setContentsMargins(2, 2, 2, 2)

        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        self._view = QComboBox()
        self._view.addItem(TIME_VIEW)
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
        self._export.setToolTip("Save the run's signals as CSV or .mat")
        self._export.clicked.connect(self._ask_export)
        self._export.setEnabled(False)
        bar.addWidget(self._export)
        root.addLayout(bar)

        self._plot = make_plot("Scope", "Time (s)", "Amplitude")
        self._plot.getPlotItem().addLegend(offset=(-10, 10))
        root.addWidget(self._plot, stretch=1)

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

        names = sorted(result.signals)
        if preferred is None:
            kept = [n for n in previous if n in result.signals]
            preferred = kept or _default_channels(result, names)

        view = self._view.currentText()
        self._view.blockSignals(True)
        self._view.clear()
        self._view.addItem(TIME_VIEW)
        for title in result.xy:
            self._view.addItem(title)
        index = self._view.findText(view)
        self._view.setCurrentIndex(max(index, 0))
        self._view.blockSignals(False)
        self._export.setEnabled(True)

        for name in names:
            check = QCheckBox(name)
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
        if self._result is not None and view in self._result.xy:
            self._draw_xy(plot, view)
            return
        apply_theme(plot, "Scope", "Time (s)", "Amplitude")
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
                label = name if data.shape[1] == 1 else f"{name}[{channel}]"
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
        apply_theme(plot, title, x_name, y_name)
        plot.addLegend(offset=(-10, 10))
        for age, old in enumerate(self._earlier(), start=1):
            if x_name in old.signals and y_name in old.signals:
                plot.plot(old.signals[x_name][:, 0], old.signals[y_name][:, 0],
                          pen=_faded(0, age), name=f"run −{age}")
        plot.plot(self._result.signals[x_name][:, 0],
                  self._result.signals[y_name][:, 0],
                  pen=curve_pen(0, 1.9), name=f"{y_name} vs {x_name}")
        self._readout.setText("")

    def export(self, path, names: list[str] | None = None):
        """Write this run's signals (all, or ``names``) to CSV or .mat."""
        from ...sim.export import export_signals
        if self._result is None:
            raise ValueError("there is no run to export yet")
        return export_signals(self._result, path, names)

    def _ask_export(self) -> None:
        if self._result is None:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export signals", "signals.csv",
            "CSV (*.csv);;MATLAB data (*.mat)")
        if path:
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
                label = name if data.shape[1] == 1 else f"{name}[{channel}]"
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
