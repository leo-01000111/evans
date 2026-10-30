"""Source blocks — signals that drive a model."""

from __future__ import annotations

import numpy as np

from ..block import Block, BlockError, ParamSpec, register

_CAT = "Sources"


@register
class Constant(Block):
    type_name = "Constant"
    category = _CAT
    description = "A fixed value."
    default_inputs = ()
    params_spec = (
        ParamSpec("value", "Value", 1.0, help="Constant output."),
    )

    @property
    def direct_feedthrough(self) -> bool:
        return False

    def output_widths(self, input_widths):
        return [np.atleast_1d(np.asarray(self.params["value"])).size]

    labels_expressions = True

    def output(self, t, x, xd, u):
        return [np.atleast_1d(np.asarray(self.params["value"], dtype=float))]

    def label(self):
        return self.shown("value")


@register
class Step(Block):
    type_name = "Step"
    category = _CAT
    description = "Step from an initial to a final value at a given time."
    default_inputs = ()
    params_spec = (
        ParamSpec("step_time", "Step time", 1.0),
        ParamSpec("initial", "Initial value", 0.0),
        ParamSpec("final", "Final value", 1.0),
    )

    @property
    def direct_feedthrough(self) -> bool:
        return False

    def output(self, t, x, xd, u):
        p = self.params
        value = p["final"] if t >= p["step_time"] else p["initial"]
        return [np.array([float(value)])]

    def zero_crossings(self, t, x, xd, u):
        # Let the solver land exactly on the step instead of straddling it,
        # which would otherwise smear the discontinuity over one step and
        # make the response depend on the step size.
        return np.array([t - self.params["step_time"]])

    def n_zero_crossings(self, input_widths):
        return 1

    def label(self):
        return "Step"


@register
class Ramp(Block):
    type_name = "Ramp"
    category = _CAT
    description = "Constant slope after a start time."
    default_inputs = ()
    params_spec = (
        ParamSpec("slope", "Slope", 1.0),
        ParamSpec("start_time", "Start time", 0.0),
        ParamSpec("initial", "Initial output", 0.0),
    )

    @property
    def direct_feedthrough(self) -> bool:
        return False

    def output(self, t, x, xd, u):
        p = self.params
        dt = max(t - p["start_time"], 0.0)
        return [np.array([p["initial"] + p["slope"] * dt])]


@register
class Sine(Block):
    type_name = "Sine"
    category = _CAT
    description = "A · sin(ω t + φ) + bias."
    default_inputs = ()
    params_spec = (
        ParamSpec("amplitude", "Amplitude", 1.0),
        ParamSpec("frequency", "Frequency (rad/s)", 1.0),
        ParamSpec("phase", "Phase (rad)", 0.0),
        ParamSpec("bias", "Bias", 0.0),
    )

    @property
    def direct_feedthrough(self) -> bool:
        return False

    def output(self, t, x, xd, u):
        p = self.params
        return [np.array([p["bias"] + p["amplitude"] *
                          np.sin(p["frequency"] * t + p["phase"])])]


@register
class Chirp(Block):
    type_name = "Chirp"
    category = _CAT
    description = "Sine sweeping linearly in frequency — one run gives a Bode plot."
    default_inputs = ()
    params_spec = (
        ParamSpec("amplitude", "Amplitude", 1.0),
        ParamSpec("f_start", "Start freq (rad/s)", 0.1),
        ParamSpec("f_end", "End freq (rad/s)", 10.0),
        ParamSpec("sweep_time", "Sweep time (s)", 10.0),
    )

    @property
    def direct_feedthrough(self) -> bool:
        return False

    def output(self, t, x, xd, u):
        p = self.params
        rate = (p["f_end"] - p["f_start"]) / max(p["sweep_time"], 1e-12)
        # Phase is the integral of the instantaneous frequency.
        phase = p["f_start"] * t + 0.5 * rate * t * t
        return [np.array([p["amplitude"] * np.sin(phase)])]


@register
class Pulse(Block):
    type_name = "Pulse"
    category = _CAT
    description = "Periodic rectangular pulse."
    default_inputs = ()
    params_spec = (
        ParamSpec("amplitude", "Amplitude", 1.0),
        ParamSpec("period", "Period (s)", 2.0),
        ParamSpec("duty", "Duty cycle (0–1)", 0.5),
        ParamSpec("delay", "Start delay (s)", 0.0),
    )

    @property
    def direct_feedthrough(self) -> bool:
        return False

    def _phase(self, t: float) -> float:
        p = self.params
        return (t - p["delay"]) % max(p["period"], 1e-12)

    def output(self, t, x, xd, u):
        p = self.params
        if t < p["delay"]:
            return [np.array([0.0])]
        on = self._phase(t) < p["duty"] * p["period"]
        return [np.array([p["amplitude"] if on else 0.0])]

    def zero_crossings(self, t, x, xd, u):
        p = self.params
        phase = self._phase(t)
        return np.array([phase - p["duty"] * p["period"]])

    def n_zero_crossings(self, input_widths):
        return 1


@register
class FromWorkspace(Block):
    """
    A signal read from the workspace: a matrix ``[t, u1, u2, …]``, a
    structure with ``time`` and ``signals.values``, or a timeseries.

    Between the samples the value is interpolated linearly, or held when
    interpolation is off; before the first sample it is the first value.
    """

    type_name = "FromWorkspace"
    category = _CAT
    description = "A signal from the workspace: [t, u] or a struct with time."
    default_inputs = ()
    params_spec = (
        ParamSpec("data", "Data", "simin", kind="data",
                  help="A variable or expression: [t, u1, u2, …] with t "
                       "increasing, or a struct with time and "
                       "signals.values."),
        ParamSpec("interpolate", "Interpolate data", True, kind="bool"),
        ParamSpec("after", "After the final value", "Extrapolation",
                  kind="choice",
                  choices=("Extrapolation", "Setting to zero",
                           "Holding final value")),
    )

    def configure(self) -> None:
        data = self.params["data"]
        if data is None or isinstance(data, str):
            # Not evaluated yet: one zero channel, until the model compiles.
            self._t, self._u = np.zeros(1), np.zeros((1, 1))
            return
        self._t, self._u = _time_and_values(data)

    @property
    def direct_feedthrough(self) -> bool:
        return False

    def output_widths(self, input_widths):
        return [int(self._u.shape[1])]

    def output(self, t, x, xd, u):
        times, values = self._t, self._u
        if t > times[-1]:
            after = self.params["after"]
            if after == "Setting to zero":
                return [np.zeros(values.shape[1])]
            if after == "Extrapolation" and len(times) > 1 \
                    and self.params["interpolate"]:
                slope = (values[-1] - values[-2]) / (times[-1] - times[-2])
                return [values[-1] + slope * (t - times[-1])]
            return [values[-1].copy()]
        if not self.params["interpolate"]:
            k = max(int(np.searchsorted(times, t, side="right")) - 1, 0)
            return [values[k].copy()]
        return [np.array([np.interp(t, times, values[:, i])
                          for i in range(values.shape[1])])]

    def label(self):
        data = self.params["data"]
        return self.expressions.get("data") or (
            data if isinstance(data, str) else "From\nWorkspace")


def _time_and_values(data) -> tuple[np.ndarray, np.ndarray]:
    """``(t, u)`` from a From Workspace block's data, or a BlockError."""
    if isinstance(data, dict):
        lowered = {str(k).lower(): v for k, v in data.items()}
        if "time" in lowered and "data" in lowered:          # a timeseries
            times, values = lowered["time"], lowered["data"]
        elif "time" in lowered and "signals" in lowered:
            signals = lowered["signals"]
            if isinstance(signals, list) and signals:
                signals = signals[0]
            try:
                values = signals["values"]
            except (KeyError, TypeError):
                raise BlockError(
                    "the struct's signals field has no values") from None
            times = lowered["time"]
        else:
            raise BlockError(
                "a struct needs fields time and signals.values (or Time and "
                "Data, as a timeseries has)")
        times = np.asarray(times, dtype=float).reshape(-1)
        values = np.asarray(values, dtype=float)
        if values.ndim == 1 or (values.ndim == 2 and values.shape[0] == 1
                                and len(times) != 1):
            values = values.reshape(-1, 1)
    else:
        try:
            matrix = np.atleast_2d(np.asarray(data, dtype=float))
        except (TypeError, ValueError):
            raise BlockError(
                "needs a matrix [t, u1, u2, …] or a struct with time and "
                "signals.values") from None
        if matrix.shape[1] < 2:
            raise BlockError(
                f"needs at least two columns, time and one signal; got a "
                f"{matrix.shape[0]}×{matrix.shape[1]} matrix")
        times, values = matrix[:, 0], matrix[:, 1:]
    if values.shape[0] != len(times):
        raise BlockError(
            f"has {len(times)} times but {values.shape[0]} rows of values")
    if len(times) == 0:
        raise BlockError("is empty")
    if np.any(np.diff(times) < 0):
        raise BlockError("its times must not decrease")
    return times, values


@register
class Clock(Block):
    type_name = "Clock"
    category = _CAT
    description = "Simulation time."
    default_inputs = ()

    @property
    def direct_feedthrough(self) -> bool:
        return False

    def output(self, t, x, xd, u):
        return [np.array([float(t)])]


@register
class BandLimitedNoise(Block):
    type_name = "Noise"
    category = _CAT
    description = "Band-limited white noise, held over a sample period."
    default_inputs = ()
    params_spec = (
        ParamSpec("power", "Noise power", 0.01),
        ParamSpec("sample_time", "Sample time (s)", 0.05),
        ParamSpec("seed", "Seed", 0, kind="int"),
    )

    def configure(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._rng = np.random.default_rng(int(self.params["seed"]))
        self._cache: dict[int, float] = {}

    @property
    def direct_feedthrough(self) -> bool:
        return False

    def output(self, t, x, xd, u):
        ts = max(self.params["sample_time"], 1e-12)
        # Key on the sample index, not on t: the ODE solver evaluates the same
        # instant repeatedly within a step, and a fresh draw each time would
        # make the "signal" depend on the solver's internal stages.
        k = int(np.floor(t / ts))
        if k not in self._cache:
            sigma = np.sqrt(max(self.params["power"], 0.0) / ts)
            self._cache[k] = float(self._rng.normal(0.0, sigma))
        return [np.array([self._cache[k]])]


@register
class PRBS(Block):
    type_name = "PRBS"
    category = _CAT
    description = "Pseudo-random binary sequence — the standard identification input."
    default_inputs = ()
    params_spec = (
        ParamSpec("amplitude", "Amplitude", 1.0),
        ParamSpec("sample_time", "Bit period (s)", 0.1),
        ParamSpec("seed", "Seed", 1, kind="int"),
    )

    def configure(self) -> None:
        if self.params["sample_time"] <= 0:
            raise BlockError("PRBS needs a positive bit period")
        self.reset()

    def reset(self) -> None:
        self._rng = np.random.default_rng(int(self.params["seed"]))
        self._cache: dict[int, float] = {}

    @property
    def direct_feedthrough(self) -> bool:
        return False

    def output(self, t, x, xd, u):
        ts = self.params["sample_time"]
        # Keyed on the bit index so every solver stage within one bit sees the
        # same value — a fresh draw per evaluation is noise, not a signal.
        k = int(np.floor(max(t, 0.0) / ts))
        if k not in self._cache:
            self._cache[k] = float(self._rng.choice([-1.0, 1.0]))
        return [np.array([self.params["amplitude"] * self._cache[k]])]

    def label(self):
        return "PRBS"


def _table(times_text, values_text, who: str) -> tuple[np.ndarray, np.ndarray]:
    from .continuous import _parse_vector
    times = _parse_vector(times_text)
    values = _parse_vector(values_text)
    if len(times) != len(values):
        raise BlockError(f"{who}: {len(times)} times but {len(values)} values")
    if np.any(np.diff(times) < 0):
        raise BlockError(f"{who}: the times must not decrease")
    return times, values


@register
class RepeatingSequence(Block):
    """
    A piecewise-linear wave through (time, value) points, repeated with a
    period equal to the last time: ``[0 2]``, ``[0 2]`` is a sawtooth.
    """

    type_name = "RepeatingSequence"
    category = _CAT
    description = "A piecewise-linear table of values, repeated forever."
    default_inputs = ()
    params_spec = (
        ParamSpec("times", "Time values", "0, 2", kind="vector"),
        ParamSpec("values", "Output values", "0, 2", kind="vector"),
    )

    def configure(self) -> None:
        self._t, self._v = _table(self.params["times"], self.params["values"],
                                  f"RepeatingSequence {self.block_id!r}")
        self._period = float(self._t[-1] - self._t[0])
        if self._period <= 0:
            raise BlockError(
                f"RepeatingSequence {self.block_id!r}: the last time must "
                f"be after the first; it sets the period")

    @property
    def direct_feedthrough(self) -> bool:
        return False

    def _phase(self, t: float) -> float:
        return self._t[0] + (t - self._t[0]) % self._period

    def output(self, t, x, xd, u):
        return [np.array([np.interp(self._phase(t), self._t, self._v)])]

    def zero_crossings(self, t, x, xd, u):
        # The wrap at each period is a jump; this value changes sign there.
        return np.array([self._phase(t) - self._t[0] - self._period / 2])

    def n_zero_crossings(self, input_widths):
        return 1

    def label(self):
        return "repeat"


@register
class SignalBuilder(Block):
    """
    A signal drawn as (time, value) points and joined by straight lines;
    the last value is held. Repeat a time to make a step: ``0 1 1 3`` with
    ``0 0 2 2`` is a step of 2 at t = 1. (Simulink's Signal Builder is
    edited on a graph; here the points are typed.)
    """

    type_name = "SignalBuilder"
    category = _CAT
    description = "A piecewise-linear signal through typed (time, value) points."
    default_inputs = ()
    params_spec = (
        ParamSpec("times", "Times", "0, 1, 1, 3, 4, 5", kind="vector"),
        ParamSpec("values", "Values", "0, 0, 1, 1, 0, 0", kind="vector"),
    )

    def configure(self) -> None:
        self._t, self._v = _table(self.params["times"], self.params["values"],
                                  f"SignalBuilder {self.block_id!r}")
        # A repeated time is a jump; the solver is told to stop on it.
        self._jumps = np.unique(self._t[1:][np.diff(self._t) == 0])

    @property
    def direct_feedthrough(self) -> bool:
        return False

    def output(self, t, x, xd, u):
        if t >= self._t[-1]:
            return [np.array([self._v[-1]])]
        if t <= self._t[0]:
            return [np.array([self._v[0]])]
        # On a repeated time, take the value after the jump.
        hi = int(np.searchsorted(self._t, t, side="right"))
        lo = hi - 1
        span = self._t[hi] - self._t[lo]
        if span <= 0:
            return [np.array([self._v[hi]])]
        w = (t - self._t[lo]) / span
        return [np.array([self._v[lo] + w * (self._v[hi] - self._v[lo])])]

    def zero_crossings(self, t, x, xd, u):
        return np.asarray(t - self._jumps, dtype=float)

    def n_zero_crossings(self, input_widths):
        return len(self._jumps)

    def label(self):
        return "signal\nbuilder"
