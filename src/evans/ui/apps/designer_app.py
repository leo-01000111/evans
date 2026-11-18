"""
The root-locus designer — sisotool, the useful half, in the Design tab.

One plot and its controls: the root locus you drag a closed-loop pole along,
the gain, and the compensator's zeros and poles. It used to carry its own
Bode and step plots as a docked app; in the side panel's Design tab the pane
grid is the display, so the designer only edits and says what changed
(`changed`), and the Design tab writes K₂ (`ui/design_panel.py`).

**Why the locus does not move when the gain does.** The locus is computed for
the compensator with its gain set to 1, so the curve on screen is fixed and
the gain is a *position along it*. Recomputing the locus for each new gain
would redraw the same curve while the marker stayed put — the opposite of what
the gesture is supposed to show.
"""

from __future__ import annotations

import control as ctl
import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ...core.designer import (
    Compensator,
    DesignSummary,
    damping_ray,
    evaluate,
    gain_for_damping,
    gain_for_overshoot,
    point_to_gain,
)
from .. import theme
from ..design import NORMAL, TIGHT
from ..guard import GuardedPanel, guard
from ..plots import (
    add_hline,
    add_vline,
    curve_pen,
    make_plot,
    widen_degenerate_range,
)

#: While the pole target is dragged, the gain is recomputed at most this
#: often. A throttle, not a debounce: a steady drag still updates.
DRAG_INTERVAL_MS = 50

#: The locus's least height in the side panel. It is the drag surface, so it
#: takes whatever height the panel has beyond what the controls need.
LOCUS_HEIGHT = 220

#: The two views of the designer, as the Design tab names them.
VIEWS = ("gain", "compensator")


class ControlSystemDesigner(QWidget, GuardedPanel):
    """Drag a closed-loop pole on the root locus; the gain follows."""

    #: The user changed the design: ``(what, final)``. ``what`` is "gain" or
    #: "compensator"; ``final`` is False while a slider or the pole target
    #: is still being dragged. Not emitted for changes made from outside
    #: (`set_plant`, `set_compensator`).
    changed = Signal(str, bool)

    def __init__(self, plant: ctl.TransferFunction | None = None,
                 compensator: Compensator | None = None,
                 sensor: ctl.TransferFunction | None = None,
                 parent=None) -> None:
        super().__init__(parent)
        self.setAccessibleName("Root locus designer")
        self._plant = plant if plant is not None else ctl.tf([1], [1, 3, 2, 0])
        self._sensor = sensor
        self.compensator = compensator or Compensator()
        self._summary: DesignSummary | None = None
        self._locus_note = ""
        self._target: pg.TargetItem | None = None
        self._pole_markers = None
        self._syncing = False

        self._drag_timer = QTimer(self)
        self._drag_timer.setSingleShot(True)
        self._drag_timer.setInterval(DRAG_INTERVAL_MS)
        self._drag_timer.timeout.connect(self._on_drag_settled)

        self._build_ui()
        self.set_compensator(self.compensator)

    # ── UI ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(NORMAL)
        self.install_error_banner(outer)

        self._locus_widget = make_plot("Root locus", "Re", "Im")
        self._locus_widget.setMinimumHeight(LOCUS_HEIGHT)
        self._locus_widget.setSizePolicy(QSizePolicy.Expanding,
                                         QSizePolicy.Expanding)
        self._locus_widget.setAccessibleName("Root locus")
        outer.addWidget(self._locus_widget, stretch=1)

        self._rays_check = QCheckBox("Show constant-ζ rays")
        self._rays_check.setChecked(True)
        self._rays_check.setAccessibleName("Show constant damping rays")
        self._rays_check.toggled.connect(self.rebuild)
        outer.addWidget(self._rays_check)

        # Gain and Compensator are two views of this one designer: the
        # locus above is shared, the controls below switch.
        self._views = QStackedWidget()
        self._views.addWidget(self._build_gain_controls())
        self._views.addWidget(self._build_compensator_controls())
        self._views.currentChanged.connect(self._size_to_current_view)
        self._size_to_current_view()
        outer.addWidget(self._views)

        self._readout = QLabel()
        self._readout.setFont(theme.data_font(9))
        self._readout.setWordWrap(True)
        self._readout.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._readout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._readout.setAccessibleName("Design readout")
        outer.addWidget(self._readout)

    def _size_to_current_view(self, *_ignored) -> None:
        """
        Only the page in view counts towards the stack's height: a
        ``QStackedWidget`` is as tall as its tallest page, which left the
        shorter view with empty space under it.
        """
        current = self._views.currentWidget()
        for index in range(self._views.count()):
            page = self._views.widget(index)
            page.setSizePolicy(
                QSizePolicy.Preferred,
                QSizePolicy.Preferred if page is current
                else QSizePolicy.Ignored)
        self._views.updateGeometry()

    def _build_gain_controls(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(TIGHT)

        self._gain_spin = QDoubleSpinBox()
        self._gain_spin.setDecimals(5)
        self._gain_spin.setRange(0.0, 1e7)
        self._gain_spin.setValue(self.compensator.gain)
        self._gain_spin.setAccessibleName("Gain K")
        self._gain_spin.valueChanged.connect(self._on_gain_typed)
        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.addRow("Gain K:", self._gain_spin)
        lay.addLayout(form)

        # A log slider: gains that matter span decades, and a linear slider
        # would spend nine tenths of its travel above the interesting range.
        self._gain_slider = QSlider(Qt.Horizontal)
        self._gain_slider.setRange(-300, 400)       # 10^-3 … 10^4
        self._gain_slider.setValue(0)
        self._gain_slider.setAccessibleName("Gain slider")
        self._gain_slider.setToolTip(
            "Gain K, on a log scale from 0.001 to 10000")
        self._gain_slider.valueChanged.connect(self._on_gain_slid)
        self._gain_slider.sliderReleased.connect(
            lambda: self._emit("gain", True))
        lay.addWidget(self._gain_slider)

        targets = QFormLayout()
        targets.setContentsMargins(0, 0, 0, 0)
        self._zeta_spin = QDoubleSpinBox()
        self._zeta_spin.setRange(0.01, 0.99)
        self._zeta_spin.setSingleStep(0.05)
        self._zeta_spin.setValue(0.5)
        self._zeta_spin.setAccessibleName("Damping target")
        zeta_btn = QPushButton("Set K for ζ")
        zeta_btn.setAccessibleName("Set K for damping")
        zeta_btn.setToolTip(
            "The gain that puts the dominant poles on this damping ratio")
        zeta_btn.clicked.connect(self._set_gain_for_damping)
        targets.addRow(self._zeta_spin, zeta_btn)

        self._mp_spin = QDoubleSpinBox()
        self._mp_spin.setRange(0.1, 99.0)
        self._mp_spin.setSuffix(" %")
        self._mp_spin.setValue(16.3)
        self._mp_spin.setAccessibleName("Overshoot target")
        mp_btn = QPushButton("Set K for overshoot")
        mp_btn.setAccessibleName("Set K for overshoot")
        mp_btn.setToolTip(
            "The gain that gives this percent overshoot, read as a damping "
            "ratio")
        mp_btn.clicked.connect(self._set_gain_for_overshoot)
        targets.addRow(self._mp_spin, mp_btn)
        lay.addLayout(targets)
        return page

    def _build_compensator_controls(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setContentsMargins(0, 0, 0, 0)
        self._zeros_edit = QLineEdit()
        self._zeros_edit.setPlaceholderText("-1, -2+3j")
        self._zeros_edit.setAccessibleName("Compensator zeros")
        self._poles_edit = QLineEdit()
        self._poles_edit.setPlaceholderText("-10, 0")
        self._poles_edit.setAccessibleName("Compensator poles")
        for edit in (self._zeros_edit, self._poles_edit):
            edit.editingFinished.connect(self._on_roots_edited)
        form.addRow("Zeros:", self._zeros_edit)
        form.addRow("Poles:", self._poles_edit)

        quick = QHBoxLayout()
        quick.setSpacing(TIGHT)
        for label, name, slot, tip in (
                ("+ integrator", "Add integrator", self._add_integrator,
                 "Add a pole at the origin: no steady-state error to a "
                 "step"),
                ("+ lead", "Add lead", self._add_lead,
                 "Add a zero at -1 and a pole at -10, a lead section to "
                 "start from")):
            button = QPushButton(label)
            button.setAccessibleName(name)
            button.setToolTip(tip)
            button.clicked.connect(slot)
            quick.addWidget(button)
        form.addRow(quick)
        return page

    # ── views ───────────────────────────────────────────────────

    @property
    def view(self) -> str:
        return VIEWS[self._views.currentIndex()]

    def set_view(self, view: str) -> None:
        """Show the gain controls or the compensator's, under the locus."""
        self._views.setCurrentIndex(VIEWS.index(view))

    def _emit(self, what: str, final: bool) -> None:
        if not self._syncing:
            self.changed.emit(what, final)

    # ── plant and compensator ───────────────────────────────────

    def set_plant(self, plant: ctl.TransferFunction,
                  sensor: ctl.TransferFunction | None = None,
                  compensator: Compensator | None = None) -> None:
        """
        A new plant (and sensor), and with ``compensator`` a new starting
        design too, in one redraw. Says nothing on `changed`.
        """
        self._plant = plant
        self._sensor = sensor
        if compensator is not None:
            self.set_compensator(compensator)
        else:
            self.rebuild()

    def set_compensator(self, compensator: Compensator) -> None:
        """Show ``compensator``. Says nothing on `changed`."""
        self.compensator = compensator
        syncing, self._syncing = self._syncing, True
        try:
            self._zeros_edit.setText(_join(compensator.zeros))
            self._poles_edit.setText(_join(compensator.poles))
            self._sync_gain_widgets()
            self.rebuild()
        finally:
            self._syncing = syncing

    def _on_roots_edited(self) -> None:
        if self._syncing:
            return
        before = (list(self.compensator.zeros), list(self.compensator.poles))
        if self.rebuild() and before != (self.compensator.zeros,
                                         self.compensator.poles):
            self._emit("compensator", True)

    def _add_integrator(self) -> None:
        self._poles_edit.setText(_append(self._poles_edit.text(), "0"))
        if self.rebuild():
            self._emit("compensator", True)

    def _add_lead(self) -> None:
        """A lead section an order of magnitude apart, as a starting point."""
        self._zeros_edit.setText(_append(self._zeros_edit.text(), "-1"))
        self._poles_edit.setText(_append(self._poles_edit.text(), "-10"))
        if self.rebuild():
            self._emit("compensator", True)

    # ── gain changes ────────────────────────────────────────────

    def _on_gain_typed(self, value: float) -> None:
        if self._syncing:
            return
        self.set_gain(float(value))
        self._emit("gain", True)

    def _on_gain_slid(self, ticks: int) -> None:
        if self._syncing:
            return
        self.set_gain(float(10.0 ** (ticks / 100.0)))
        self._emit("gain", not self._gain_slider.isSliderDown())

    def set_gain(self, gain: float) -> None:
        self.compensator.gain = max(float(gain), 0.0)
        self._sync_gain_widgets()
        self.update_gain()

    def _sync_gain_widgets(self) -> None:
        syncing, self._syncing = self._syncing, True
        self._gain_spin.setValue(self.compensator.gain)
        if self.compensator.gain > 0:
            self._gain_slider.setValue(
                int(round(100.0 * np.log10(self.compensator.gain))))
        self._syncing = syncing

    # ── dragging ────────────────────────────────────────────────

    def _on_target_moved(self) -> None:
        if self._syncing or self._target is None:
            return
        if not self._drag_timer.isActive():
            self._drag_timer.start()

    def _on_drag_settled(self) -> None:
        if self._target is None:
            return
        pos = self._target.pos()
        self.pick_point(complex(pos.x(), pos.y()), snap=False)
        self._emit("gain", False)

    def _on_target_released(self) -> None:
        self._drag_timer.stop()
        if self._target is None:
            return
        pos = self._target.pos()
        self.pick_point(complex(pos.x(), pos.y()), snap=True)
        self._emit("gain", True)

    @guard("pole placement")
    def pick_point(self, point: complex, snap: bool = True) -> None:
        """
        Set the gain so a closed-loop pole lands as near ``point`` as the
        locus allows. ``snap`` moves the marker onto the pole it actually got.
        """
        if self._summary is None:
            return
        result = point_to_gain(_unit_loop(self._plant, self.compensator,
                                          self._sensor),
                               point, locus=self._summary.locus)
        self.compensator.gain = result.K
        self._sync_gain_widgets()
        self.update_gain()
        if snap:
            self._move_target(result.pole)

    def _move_target(self, pole: complex) -> None:
        if self._target is None:
            return
        syncing, self._syncing = self._syncing, True
        self._target.setPos(pg.Point(float(pole.real), float(pole.imag)))
        self._syncing = syncing

    # ── design targets ──────────────────────────────────────────

    @guard("damping target")
    def _set_gain_for_damping(self) -> None:
        self._apply_target(gain_for_damping(
            _unit_loop(self._plant, self.compensator, self._sensor),
            float(self._zeta_spin.value())),
            f"ζ = {self._zeta_spin.value():.2f}")

    @guard("overshoot target")
    def _set_gain_for_overshoot(self) -> None:
        self._apply_target(gain_for_overshoot(
            _unit_loop(self._plant, self.compensator, self._sensor),
            float(self._mp_spin.value())),
            f"{self._mp_spin.value():.1f}% overshoot")

    def _apply_target(self, point, description: str) -> None:
        if point is None:
            self.report_error(
                "design target",
                ValueError(f"No gain on this locus gives {description}. "
                           f"The branches never reach that damping — add a "
                           f"lead section to bend them left."))
            return
        self.compensator.gain = point.K
        self._sync_gain_widgets()
        self.update_gain()
        self._move_target(point.pole)
        self._emit("gain", True)

    # ── drawing ─────────────────────────────────────────────────

    @guard("designer")
    def rebuild(self, *_ignored) -> bool:
        """Full redraw — the compensator's poles or zeros changed."""
        self.compensator.zeros = _parse(self._zeros_edit.text())
        self.compensator.poles = _parse(self._poles_edit.text())
        if not self.compensator.is_real_coefficient():
            raise ValueError(
                "A complex root needs its conjugate too, or the compensator "
                "has complex coefficients and cannot be built from real "
                "components. Add the mirrored root.")
        self._target = None
        self._pole_markers = None
        summary = evaluate(self._plant, self.compensator, self._sensor)
        self._summary = summary
        self._draw_locus(summary)
        self._draw_linked(summary)
        return True

    @guard("designer")
    def update_gain(self, *_ignored) -> None:
        """Cheap redraw — only the gain changed, so the locus stays put."""
        locus = self._summary.locus if self._summary is not None else None
        summary = evaluate(self._plant, self.compensator, self._sensor,
                           locus=locus)
        self._summary = summary
        self._draw_linked(summary)

    def _draw_linked(self, summary: DesignSummary) -> None:
        self._draw_closed_loop_poles(summary)
        lines = [summary.describe()]
        if self._locus_note:
            lines.append(self._locus_note)
        self._readout.setText("\n".join(lines))

    def _draw_locus(self, summary: DesignSummary) -> None:
        plot = self._locus_widget.getPlotItem()
        plot.clear()
        locus = summary.locus

        for branch in range(locus.roots.shape[1]):
            roots = locus.roots[:, branch]
            ok = np.isfinite(roots)
            plot.plot(roots[ok].real, roots[ok].imag,
                      pen=curve_pen(branch, 1.6))

        L_unit = _unit_loop(self._plant, self.compensator, self._sensor)
        for root, symbol, colour in (
                (np.atleast_1d(ctl.poles(L_unit)), "x", theme.plot_colour("danger")),
                (np.atleast_1d(ctl.zeros(L_unit)), "o", theme.plot_colour("data"))):
            if len(root):
                plot.plot(root.real, root.imag, pen=None, symbol=symbol,
                          symbolSize=14, symbolPen=pg.mkPen(colour, width=2.4),
                          symbolBrush=None)

        add_vline(plot, 0.0, theme.plot_colour("muted"), width=0.8)
        add_hline(plot, 0.0, theme.plot_colour("muted"), width=0.8)
        _frame(plot, locus.roots)

        if self._rays_check.isChecked():
            self._draw_damping_rays(plot, locus.roots)

        # The marginal gain goes in the readout, not the title. A title long
        # enough to outgrow its panel lays the whole plot out wider than the
        # scene and pushes the curves off the edge — see `plots.set_title`.
        self._locus_note = (
            f"locus crosses the imaginary axis at K = {locus.K_marginal:.4g}, "
            f"ω = {locus.omega_marginal:.4g}"
            if np.isfinite(locus.K_marginal)
            else "the locus never crosses the imaginary axis for K > 0")

        self._install_target(plot, summary)

    def _draw_damping_rays(self, plot, roots: np.ndarray) -> None:
        finite = roots[np.isfinite(roots)]
        radius = float(np.max(np.abs(finite))) if len(finite) else 1.0
        for zeta in (0.2, 0.4, 0.6, 0.8):
            ray = damping_ray(zeta, radius * 1.2)
            for sign in (1, -1):
                plot.plot(ray.real, sign * ray.imag,
                          pen=pg.mkPen(theme.plot_colour("grid"), width=0.9,
                                       style=Qt.DotLine))

    def _install_target(self, plot, summary: DesignSummary) -> None:
        """The draggable marker, placed on the dominant closed-loop pole."""
        poles = summary.closed_loop_poles
        if not len(poles):
            return
        dominant = max(poles, key=lambda p: p.real)
        self._target = pg.TargetItem(
            pos=(float(dominant.real), float(dominant.imag)),
            size=14, symbol="s", movable=True,
            pen=pg.mkPen(theme.plot_line_highlight(), width=2.5),
            hoverPen=pg.mkPen(theme.plot_colour("reference"), width=3.0),
            label="drag me",
        )
        self._target.sigPositionChanged.connect(self._on_target_moved)
        self._target.sigPositionChangeFinished.connect(self._on_target_released)
        plot.addItem(self._target)

    def _draw_closed_loop_poles(self, summary: DesignSummary) -> None:
        plot = self._locus_widget.getPlotItem()
        if self._pole_markers is not None:
            plot.removeItem(self._pole_markers)
            self._pole_markers = None
        poles = summary.closed_loop_poles
        if not len(poles):
            return
        self._pole_markers = pg.ScatterPlotItem(
            x=poles.real, y=poles.imag, symbol="s", size=11,
            pen=pg.mkPen(theme.plot_line_highlight(), width=2.0),
            brush=pg.mkBrush(_translucent(theme.plot_line_highlight())))
        plot.addItem(self._pole_markers)


# ──────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────


def _translucent(colour: str, alpha: int = 128) -> QColor:
    c = QColor(colour)
    c.setAlpha(alpha)
    return c


def _unit_loop(plant, compensator: Compensator, sensor):
    """``C/K · G · H`` — the loop whose root locus the gain slides along."""
    unit = Compensator(1.0, list(compensator.zeros), list(compensator.poles))
    H = sensor if sensor is not None else ctl.TransferFunction([1], [1])
    return unit.tf() * plant * H


def _parse(text: str) -> list[complex]:
    """
    Parse a comma-separated root list.

    Parsing happens here, inside a guarded caller, rather than in the line
    edit's own slot — a typo then shows up in the error banner instead of
    escaping as an unhandled exception from a Qt signal.
    """
    roots: list[complex] = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            roots.append(complex(part.replace(" ", "")))
        except ValueError as exc:
            raise ValueError(
                f"{part!r} is not a number. Write roots as -1, -2.5, or "
                f"-1+2j for a complex one.") from exc
    return roots


def _join(roots: list[complex]) -> str:
    return ", ".join(
        f"{r.real:g}" if abs(r.imag) < 1e-12 else f"{r.real:g}{r.imag:+g}j"
        for r in roots)


def _append(text: str, item: str) -> str:
    text = text.strip()
    return f"{text}, {item}" if text else item


def _frame(plot, roots: np.ndarray) -> None:
    """Frame the locus without letting round-off set the scale."""
    finite = roots[np.isfinite(roots)]
    if not len(finite):
        return
    x_lo, x_hi = float(np.min(finite.real)), float(np.max(finite.real))
    y_top = float(np.max(np.abs(finite.imag)))
    (x_lo, x_hi), (y_lo, y_hi) = widen_degenerate_range(x_lo, x_hi, -y_top, y_top)
    span = max(x_hi - x_lo, 1e-9)
    y_span = max(0.5 * (y_hi - y_lo), 0.25 * span)
    plot.setXRange(x_lo - 0.2 * span, x_hi + 0.2 * span, padding=0)
    plot.setYRange(-1.2 * y_span, 1.2 * y_span, padding=0)
