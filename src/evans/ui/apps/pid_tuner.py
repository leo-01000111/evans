"""
The PID tuner — two sliders, and an honest account of what they do.

MATLAB's tuner hides the meaning of its sliders. This one prints it: the
response-time slider sets the target crossover frequency, the transient slider
sets the target phase margin, and the readout says which values were asked for
and which were achieved. When a target is impossible, the readout says why
rather than quietly returning gains that do something else.

It lives in the side panel's Design tab and says on `changed` when the user
moved something so the Design tab can write the controller into K₂. The pane
grid is the main display; the page keeps one small plot of its own, over the
sliders and filling the height the panel has: the closed-loop step response
of the tuned loop, with a Step · Bode · Nichols switch (Bode and Nichols
show the open loop). It is the panes' own renderer (a compact `LTIViewer`)
and follows the sliders at most every `PLOT_INTERVAL_MS`.
"""

from __future__ import annotations

import control as ctl
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ...core.collection import SystemCollection
from ...core.pidlimits import (
    LIMIT_KINDS,
    LimitsResult,
    crossing_time,
    limit_zones,
    tune_to_limits,
)
from ...core.pidtune import (
    PIDKind,
    TuneResult,
    crossover_for,
    phase_margin_for,
    tune,
)
from ...core.viewer import ResponseKind
from .. import theme
from ..design import NORMAL, TIGHT
from ..guard import GuardedPanel, guard

#: Slider travel. Both run over integers so the widget behaves; the mapping to
#: physical quantities lives in :mod:`evans.core.pidtune`.
SPEED_TICKS = 100          # −100 … +100  ⇒  speed −1 … +1
TRANSIENT_TICKS = 100      # 0 … 100      ⇒  transient 0 … 1

#: Limits tuning: each limit's starting value and spin-box range/decimals.
LIMIT_DEFAULTS: dict[str, tuple[float, float, float, int]] = {
    "overshoot": (10.0, 0.0, 200.0, 1),
    "rise": (1.0, 0.001, 10000.0, 3),
    "settling": (5.0, 0.001, 10000.0, 3),
    "dc_error": (1.0, 0.0, 100.0, 2),
    "phase_margin": (45.0, 0.0, 120.0, 1),
    "gain_margin": (6.0, 0.0, 60.0, 1),
}

#: The plot follows the sliders at most this often (the Design tab's rate).
PLOT_INTERVAL_MS = 50
#: The plot's least height in the side panel; it takes any height beyond.
PLOT_MIN_HEIGHT = 220
#: The plot's views, in the order of the switch.
PLOT_VIEWS = (ResponseKind.STEP, ResponseKind.BODE, ResponseKind.NICHOLS)


class PIDTuner(QWidget, GuardedPanel):
    """Tune a PID for a plant from two targets."""

    #: The user changed the design; ``final`` is False while a slider is
    #: still held. Not emitted for changes made from outside (`set_plant`,
    #: `set_kind`).
    changed = Signal(bool)

    def __init__(self, plant: ctl.TransferFunction | None = None,
                 kind: PIDKind | str = PIDKind.PI,
                 sensor: ctl.TransferFunction | None = None,
                 feedforward: ctl.TransferFunction | None = None,
                 parent=None) -> None:
        super().__init__(parent)
        self.setAccessibleName("PID tuner")
        self._plant = plant if plant is not None else ctl.tf([1], [1, 3, 3, 1])
        #: H and K₁ of the loop the controller will live in. Without them the
        #: tuning would silently assume both are 1, and disagree with the
        #: panes the moment either is not.
        self._sensor = sensor
        self._feedforward = feedforward
        self.result: TuneResult | None = None
        #: The last limits-tuning outcome; cleared when a slider takes over.
        self.limits_result: LimitsResult | None = None
        self._quiet = True
        self._plot_kind = ResponseKind.STEP
        self._plot_dirty = True
        self._plot_timer = QTimer(self)
        self._plot_timer.setSingleShot(True)
        self._plot_timer.setInterval(PLOT_INTERVAL_MS)
        self._plot_timer.timeout.connect(self._draw_plot)
        self._build_ui()
        self._kind_combo.setCurrentText(PIDKind(kind).value)
        self._quiet = False
        self.retune()

    # ── UI ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(NORMAL)
        self.install_error_banner(lay)

        # ── the plot, over the sliders, taking the free height ──
        switch = QHBoxLayout()
        switch.setContentsMargins(0, 0, 0, 0)
        switch.setSpacing(0)
        self._plot_group = QButtonGroup(self)
        self._plot_group.setExclusive(True)
        self._plot_buttons: dict[ResponseKind, QPushButton] = {}
        for view in PLOT_VIEWS:
            button = QPushButton(view.value)
            button.setCheckable(True)
            button.setAccessibleName(f"{view.value} plot")
            button.setToolTip({
                ResponseKind.STEP: "Closed-loop step response",
                ResponseKind.BODE: "Bode plot of the open loop",
                ResponseKind.NICHOLS: "Nichols chart of the open loop",
            }[view])
            button.clicked.connect(
                lambda _checked=False, v=view: self.set_plot_view(v))
            self._plot_group.addButton(button)
            self._plot_buttons[view] = button
            switch.addWidget(button, stretch=1)
        self._plot_buttons[ResponseKind.STEP].setChecked(True)
        lay.addLayout(switch)

        from .lti_viewer import LTIViewer
        self._viewer = LTIViewer(SystemCollection(), compact=True)
        self._viewer.setAccessibleName("PID response plot")
        self._viewer.setMinimumHeight(PLOT_MIN_HEIGHT)
        self._viewer.setSizePolicy(QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        lay.addWidget(self._viewer, stretch=1)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        self._kind_combo = QComboBox()
        self._kind_combo.addItems([k.value for k in PIDKind])
        self._kind_combo.setAccessibleName("Controller type")
        self._kind_combo.currentIndexChanged.connect(
            lambda _i: self._on_user_change(True))
        form.addRow("Controller:", self._kind_combo)

        self._tf_spin = QDoubleSpinBox()
        self._tf_spin.setRange(0.0, 10.0)
        self._tf_spin.setDecimals(4)
        self._tf_spin.setSingleStep(0.01)
        self._tf_spin.setAccessibleName("Derivative filter time constant")
        self._tf_spin.setToolTip(
            "Derivative filter time constant. Applied after the gains are "
            "solved, so it shifts the achieved margin slightly.")
        self._tf_spin.valueChanged.connect(
            lambda _v: self._on_user_change(True))
        form.addRow("Tf (D filter):", self._tf_spin)
        lay.addLayout(form)

        # ── the two sliders ──
        self._speed_label = QLabel()
        self._speed_label.setWordWrap(True)
        lay.addWidget(self._speed_label)
        self._speed = QSlider(Qt.Horizontal)
        self._speed.setRange(-SPEED_TICKS, SPEED_TICKS)
        self._speed.setValue(0)
        self._speed.setAccessibleName("Response time")
        self._speed.valueChanged.connect(
            lambda _v: self._on_user_change(not self._speed.isSliderDown()))
        self._speed.sliderReleased.connect(lambda: self._on_user_change(True))
        lay.addWidget(self._speed)
        lay.addWidget(_ends("slower", "faster"))

        self._transient_label = QLabel()
        self._transient_label.setWordWrap(True)
        lay.addWidget(self._transient_label)
        self._transient = QSlider(Qt.Horizontal)
        self._transient.setRange(0, TRANSIENT_TICKS)
        self._transient.setValue(TRANSIENT_TICKS // 2)
        self._transient.setAccessibleName("Transient behaviour")
        self._transient.valueChanged.connect(
            lambda _v: self._on_user_change(
                not self._transient.isSliderDown()))
        self._transient.sliderReleased.connect(
            lambda: self._on_user_change(True))
        lay.addWidget(self._transient)
        lay.addWidget(_ends("aggressive", "robust"))

        self._readout = QLabel()
        self._readout.setFont(theme.data_font(9))
        self._readout.setWordWrap(True)
        self._readout.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._readout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._readout.setAccessibleName("Tuning readout")
        lay.addWidget(self._readout)

        self._build_limits(lay)

        reset = QPushButton("Reset sliders")
        reset.setAccessibleName("Reset sliders")
        reset.setToolTip("Both sliders back to the middle")
        reset.clicked.connect(self.reset)
        lay.addWidget(reset, alignment=Qt.AlignLeft)

    def _build_limits(self, lay: QVBoxLayout) -> None:
        """The collapsible Limits tuning section."""
        self._limits_toggle = QPushButton("Limits tuning ▸")
        self._limits_toggle.setCheckable(True)
        self._limits_toggle.setAccessibleName("Limits tuning")
        self._limits_toggle.setToolTip(
            "State the step response you need (overshoot, settling time, DC "
            "error, margins) and let an optimiser find the gains.")
        lay.addWidget(self._limits_toggle)

        self._limits_box = QWidget()
        box = QFormLayout(self._limits_box)
        box.setContentsMargins(0, 0, 0, 0)
        self._limit_checks: dict[str, QCheckBox] = {}
        self._limit_spins: dict[str, QDoubleSpinBox] = {}
        for key, (label, unit, direction) in LIMIT_KINDS.items():
            default, lo, hi, decimals = LIMIT_DEFAULTS[key]
            check = QCheckBox(label)
            check.setAccessibleName(f"Limit {label}")
            spin = QDoubleSpinBox()
            spin.setRange(lo, hi)
            spin.setDecimals(decimals)
            spin.setValue(default)
            spin.setSuffix(f" {unit}")
            spin.setPrefix("≤ " if direction == "max" else "≥ ")
            spin.setAccessibleName(f"{label} limit value")
            spin.setEnabled(False)
            check.toggled.connect(spin.setEnabled)
            self._limit_checks[key] = check
            self._limit_spins[key] = spin
            box.addRow(check, spin)
        self._band_combo = QComboBox()
        self._band_combo.addItems(["±2 %", "±5 %"])
        self._band_combo.setAccessibleName("Settling band")
        self._band_combo.setToolTip("The band the settling time is measured to")
        self._band_combo.currentIndexChanged.connect(
            lambda _i: self._zones_changed())
        box.addRow("Settling band:", self._band_combo)
        for key in LIMIT_KINDS:
            self._limit_checks[key].toggled.connect(
                lambda _on: self._zones_changed())
            self._limit_spins[key].valueChanged.connect(
                lambda _v: self._zones_changed())
        self._limits_run = QPushButton("Tune to limits")
        self._limits_run.setAccessibleName("Tune to limits")
        self._limits_run.setToolTip(
            "Search for gains of the chosen controller type that meet every "
            "ticked limit. Takes a few seconds.")
        self._limits_run.clicked.connect(self.tune_to_limits)
        box.addRow(self._limits_run)
        self._limits_status = QLabel()
        self._limits_status.setFont(theme.data_font(9))
        self._limits_status.setWordWrap(True)
        self._limits_status.setAccessibleName("Limits report")
        box.addRow(self._limits_status)
        self._limits_box.setVisible(False)
        self._limits_toggle.toggled.connect(self._on_limits_toggled)
        lay.addWidget(self._limits_box)

    def _on_limits_toggled(self, on: bool) -> None:
        self._limits_toggle.setText("Limits tuning ▾" if on
                                    else "Limits tuning ▸")
        self._limits_box.setVisible(on)
        self._zones_changed()

    @property
    def settling_band(self) -> float:
        return 0.05 if self._band_combo.currentIndex() == 1 else 0.02

    def _zones_changed(self) -> None:
        """Shade the ticked limits on the step plot, if the section is open."""
        if not hasattr(self, "_viewer"):
            return
        self._plot_dirty = True
        self._schedule_plot()

    def _zones(self) -> list:
        if not self._limits_toggle.isChecked():
            return []
        t10 = 0.0
        if self.result is not None and self.result.feasible                 and self.result.stable and "rise" in self.limits:
            try:
                from ...core.timeresp import step_response
                resp = step_response(self.result.T)
                y = np.asarray(resp.y).ravel()
                y_inf = resp.metadata.get("y_inf_exact", y[-1])
                t10 = crossing_time(resp.t, y, 0.1 * float(y_inf)) or 0.0
            except Exception:                               # noqa: BLE001
                t10 = 0.0
        return limit_zones(self.limits, self.settling_band, t10)

    # ── limits tuning ───────────────────────────────────────────

    def set_limit(self, key: str, value: float | None) -> None:
        """Tick a limit and give it ``value``; ``None`` unticks it."""
        if key not in LIMIT_KINDS:
            raise ValueError(f"unknown limit {key!r}")
        if value is not None:
            self._limit_spins[key].setValue(float(value))
        self._limit_checks[key].setChecked(value is not None)

    @property
    def limits(self) -> dict[str, float]:
        """The ticked limits, key → value."""
        return {k: self._limit_spins[k].value()
                for k, c in self._limit_checks.items() if c.isChecked()}

    @guard("Limits tuning")
    def tune_to_limits(self, *_ignored) -> LimitsResult | None:
        """Search gains that meet the ticked limits and use them."""
        limits = self.limits
        if not limits:
            self._limits_status.setText("Tick at least one limit.")
            return None
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self._limits_run.setEnabled(False)
        try:
            found = tune_to_limits(
                self._plant, self.kind, limits,
                Tf=float(self._tf_spin.value()),
                sensor=self._sensor, feedforward=self._feedforward,
                settling_band=self.settling_band)
        finally:
            self._limits_run.setEnabled(True)
            QApplication.restoreOverrideCursor()
        self.limits_result = found
        self.result = found.tune
        self._limits_status.setText(found.describe())
        self._readout.setText(found.tune.describe())
        self._plot_dirty = True
        self._schedule_plot()
        self.changed.emit(True)
        return found

    # ── state ───────────────────────────────────────────────────

    def set_plant(self, plant: ctl.TransferFunction,
                  sensor: ctl.TransferFunction | None = None,
                  feedforward: ctl.TransferFunction | None = None) -> None:
        """A new loop to tune for. Says nothing on `changed`."""
        self._plant = plant
        self._sensor = sensor
        self._feedforward = feedforward
        self.retune()

    def set_kind(self, kind: PIDKind | str) -> None:
        """Choose the controller type. Says nothing on `changed`."""
        self._quiet = True
        try:
            self._kind_combo.setCurrentText(PIDKind(kind).value)
        finally:
            self._quiet = False
        self.retune()

    # ── the plot ────────────────────────────────────────────────

    @property
    def plot_view(self) -> ResponseKind:
        """Step, Bode or Nichols."""
        return self._plot_kind

    def set_plot_view(self, view: ResponseKind) -> None:
        """Choose what the plot shows."""
        if view not in PLOT_VIEWS:
            raise ValueError(f"the PID plot does not show {view.value!r}")
        self._plot_buttons[view].setChecked(True)
        self._plot_kind = view
        self._plot_dirty = True
        self._draw_plot()

    def _schedule_plot(self) -> None:
        """Redraw at most every `PLOT_INTERVAL_MS`, and only when in sight."""
        if self.isVisible() and not self._plot_timer.isActive():
            self._plot_timer.start()

    def _draw_plot(self) -> None:
        result = self.result
        if result is None or not result.feasible or not self.isVisible():
            return
        collection = SystemCollection()
        if self._plot_kind is ResponseKind.STEP:
            collection.add("Closed loop", result.T)
        else:
            collection.add("Open loop", result.L)
        self._viewer.collection = collection
        self._viewer.zones = self._zones()
        self._viewer.set_response(self._plot_kind)
        self._viewer.refresh()
        self._plot_dirty = False

    def showEvent(self, event) -> None:              # noqa: N802 (Qt API)
        super().showEvent(event)
        if self._plot_dirty:
            self._draw_plot()

    def _seen_plant(self) -> ctl.TransferFunction:
        """``G·H`` — the plant as the controller sees it, round the loop."""
        if self._sensor is None:
            return self._plant
        return self._plant * self._sensor

    @property
    def kind(self) -> PIDKind:
        return PIDKind(self._kind_combo.currentText())

    @property
    def speed(self) -> float:
        return self._speed.value() / SPEED_TICKS

    @property
    def transient(self) -> float:
        return self._transient.value() / TRANSIENT_TICKS

    def reset(self) -> None:
        """Both sliders to the middle, as one change."""
        self._quiet = True
        try:
            self._speed.setValue(0)
            self._transient.setValue(TRANSIENT_TICKS // 2)
        finally:
            self._quiet = False
        self._on_user_change(True)

    def _on_user_change(self, final: bool) -> None:
        if self._quiet:
            return
        self.retune()
        self.changed.emit(final)

    # ── tuning ──────────────────────────────────────────────────

    @guard("PID tuner")
    def retune(self, *_ignored) -> None:
        self.limits_result = None
        if hasattr(self, "_limits_status"):
            self._limits_status.clear()
        pm = phase_margin_for(self.transient)
        wc = crossover_for(self._seen_plant(), self.speed, pm, self.kind)
        self._speed_label.setText(
            f"Response time — target ωc = {wc:.4g} rad/s "
            f"(≈ {2.0 / wc:.3g} s)")
        self._transient_label.setText(
            f"Transient behaviour — target phase margin = {pm:.1f}°")

        result = tune(self._plant, self.kind, wc=wc, pm_deg=pm,
                      Tf=float(self._tf_spin.value()),
                      sensor=self._sensor, feedforward=self._feedforward)
        self.result = result
        if result.feasible:
            self._plot_dirty = True
            self._schedule_plot()
            self._readout.setText(result.describe())
        else:
            # Not an exception: an impossible target is a legitimate answer,
            # and the reason is already on screen. Raising here would bury a
            # clear explanation under a traceback.
            self._readout.setText(
                f"{result.describe()}\n\n"
                f"Move the response-time slider and the target moves with "
                f"it. K₂ keeps the last controller that could be built.")


def _settles(system: ctl.TransferFunction) -> bool:
    """Every pole strictly in the left half-plane (the Model's tune dialog)."""
    poles = np.atleast_1d(ctl.poles(system))
    return bool(np.all(poles.real < 0))


def _ends(left: str, right: str) -> QWidget:
    """The two end-labels under a slider."""
    widget = QWidget()
    row = QHBoxLayout(widget)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(TIGHT)
    for text, align in ((left, Qt.AlignLeft), (right, Qt.AlignRight)):
        label = QLabel(text)
        label.setStyleSheet("color: palette(mid); font-size: 10px;")
        row.addWidget(label, alignment=align)
    row.insertStretch(1, 1)
    return widget
