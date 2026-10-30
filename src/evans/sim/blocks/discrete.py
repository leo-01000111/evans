"""
Discrete-time blocks.

These are why the engine is hand-written rather than built on
``control.interconnect``: a discrete controller driving a continuous plant is
the ordinary case in this course, and ``interconnect`` refuses it outright
with ``ValueError: Systems have incompatible timebases``.

Every block here declares a positive :attr:`~evans.sim.block.Block.sample_time`.
The solver collects those, schedules the union of their sample hits, and forces
the continuous integrator to land exactly on each one — so the hold is updated
at the right instant regardless of what step size the ODE solver chose.
"""

from __future__ import annotations

import control as ctl
import numpy as np

from ..block import Block, BlockError, ParamSpec, as_array, register
from .continuous import _parse_vector

_CAT = "Discrete"


class _DiscreteBase(Block):
    """
    Shared sample-time handling.

    **Discrete blocks sample their inputs and hold their outputs.** A block
    here never has direct feedthrough, even when its ``D`` matrix is non-zero:
    it reads the input at a sample hit, computes, and holds that value until
    the next hit.

    This is what a sampled controller actually does, and getting it wrong is
    easy to miss. An earlier version let the proportional term of
    ``DiscretePID`` pass the *live* continuous error straight through, so a
    50 Hz controller produced a control signal that changed at every solver
    step — 1498 changes over 3 s instead of 150. It looked plausible on a
    plot and was not a sampled controller at all.

    A pleasant consequence: because nothing here feeds through, every discrete
    block breaks an algebraic loop, which is why ``UnitDelay`` is the standard
    remedy for one.
    """

    def _check_sample_time(self) -> None:
        if self.params.get("sample_time", 0.0) <= 0:
            raise BlockError(
                f"{self.type_name} {self.block_id!r} needs a positive sample "
                f"time; use the continuous equivalent for sample_time = 0"
            )

    @property
    def sample_time(self) -> float:
        return float(self.params["sample_time"])

    @property
    def direct_feedthrough(self) -> bool:
        return False


@register
class UnitDelay(_DiscreteBase):
    type_name = "UnitDelay"
    category = _CAT
    description = "z⁻¹ — one sample of delay. The standard way to break an algebraic loop."
    params_spec = (
        ParamSpec("sample_time", "Sample time (s)", 0.1),
        ParamSpec("x0", "Initial output", 0.0),
    )

    def configure(self) -> None:
        self._check_sample_time()

    @property
    def n_dstates(self) -> int:
        return 1

    @property
    def direct_feedthrough(self) -> bool:
        # The whole point: the output is last sample's input, so it never
        # reads the present one.
        return False

    def initial_discrete_state(self):
        return np.array([float(self.params["x0"])])

    def output(self, t, x, xd, u):
        return [xd.copy()]

    def update(self, t, x, xd, u):
        return np.atleast_1d(u[0])[:1].astype(float) if u else xd

    def label(self):
        return "1/z"


@register
class ZeroOrderHold(_DiscreteBase):
    type_name = "ZeroOrderHold"
    category = _CAT
    description = "Sample and hold — the D/A converter at a controller's output."
    params_spec = (ParamSpec("sample_time", "Sample time (s)", 0.1),)

    def configure(self) -> None:
        self._check_sample_time()

    @property
    def n_dstates(self) -> int:
        return 1

    @property
    def direct_feedthrough(self) -> bool:
        return False

    def output(self, t, x, xd, u):
        return [xd.copy()]

    def update(self, t, x, xd, u):
        return np.atleast_1d(u[0])[:1].astype(float) if u else xd

    def label(self):
        return "ZOH"


@register
class DiscreteTransferFcn(_DiscreteBase):
    type_name = "DiscreteTF"
    category = _CAT
    description = "num(z)/den(z), updated at each sample."
    params_spec = (
        ParamSpec("num", "Numerator (z)", "1", kind="vector"),
        ParamSpec("den", "Denominator (z)", "1, -0.5", kind="vector"),
        ParamSpec("sample_time", "Sample time (s)", 0.1),
    )

    def configure(self) -> None:
        self._check_sample_time()
        num = _parse_vector(self.params["num"])
        den = _parse_vector(self.params["den"])
        if len(num) > len(den):
            raise BlockError(
                f"DiscreteTF {self.block_id!r} is non-causal "
                f"(numerator order exceeds denominator order)"
            )
        self.tf = ctl.TransferFunction(num, den, float(self.params["sample_time"]))
        ss = ctl.tf2ss(self.tf)
        self._A = np.atleast_2d(np.asarray(ss.A, dtype=float))
        self._B = np.atleast_2d(np.asarray(ss.B, dtype=float)).reshape(-1, 1)
        self._C = np.atleast_2d(np.asarray(ss.C, dtype=float)).reshape(1, -1)
        self._D = np.atleast_2d(np.asarray(ss.D, dtype=float)).reshape(1, 1)
        if self._A.size == 0:
            self._A = np.zeros((0, 0))
            self._B = np.zeros((0, 1))
            self._C = np.zeros((1, 0))

    @property
    def n_dstates(self) -> int:
        # The realisation's own states, plus one slot holding the output
        # between sample hits.
        return int(self._A.shape[0]) + 1

    def output_widths(self, input_widths):
        return [1]

    def output(self, t, x, xd, u):
        return [xd[-1:].copy()]

    def update(self, t, x, xd, u):
        uu = np.atleast_1d(u[0])[:1] if u else np.zeros(1)
        n = int(self._A.shape[0])
        state = xd[:n]
        y = self._C @ state + self._D @ uu
        return np.concatenate([self._A @ state + self._B @ uu,
                               np.atleast_1d(y)])

    def label(self):
        return f"H(z)\nTs={self.params['sample_time']:g}"


@register
class DiscretePID(_DiscreteBase):
    type_name = "DiscretePID"
    category = _CAT
    description = "PID in a sampled loop, with backward-Euler integration."
    params_spec = (
        ParamSpec("Kp", "Kp", 1.0),
        ParamSpec("Ki", "Ki", 0.0),
        ParamSpec("Kd", "Kd", 0.0),
        ParamSpec("sample_time", "Sample time (s)", 0.1),
        ParamSpec("limit", "Limit output", False, kind="bool"),
        ParamSpec("upper", "Upper limit", 1.0),
        ParamSpec("lower", "Lower limit", -1.0),
    )

    def configure(self) -> None:
        self._check_sample_time()

    @property
    def n_dstates(self) -> int:
        # [integral accumulator, previous error, held output]
        return 3

    def _raw(self, xd, e):
        p = self.params
        derivative = (e - xd[1]) / self.sample_time
        return p["Kp"] * e + p["Ki"] * xd[0] + p["Kd"] * derivative

    def output(self, t, x, xd, u):
        return [xd[2:3].copy()]

    def update(self, t, x, xd, u):
        p = self.params
        ts = self.sample_time
        e = float(np.atleast_1d(u[0])[0]) if u else 0.0

        v = self._raw(xd, e)
        saturated = p["limit"] and not (p["lower"] <= v <= p["upper"])
        if p["limit"]:
            v = float(np.clip(v, p["lower"], p["upper"]))

        # Conditional integration: stop accumulating while the output is held
        # at a limit and the error would push it further out, so the
        # integrator has no charge to unwind when the error reverses.
        integral = xd[0]
        if not (saturated and ((v >= p["upper"] and e > 0) or
                               (v <= p["lower"] and e < 0))):
            integral = xd[0] + e * ts
        return np.array([integral, e, v])

    def label(self):
        return f"PID(z)\nTs={self.params['sample_time']:g}"


@register
class DiscreteStateSpace(_DiscreteBase):
    type_name = "DiscreteSS"
    category = _CAT
    description = "x[k+1] = Ax[k] + Bu[k],  y[k] = Cx[k] + Du[k]."
    params_spec = (
        ParamSpec("A", "A", "0.5", kind="matrix"),
        ParamSpec("B", "B", "1", kind="matrix"),
        ParamSpec("C", "C", "1", kind="matrix"),
        ParamSpec("D", "D", "0", kind="matrix"),
        ParamSpec("sample_time", "Sample time (s)", 0.1),
        ParamSpec("x0", "Initial state", 0.0),
    )

    def configure(self) -> None:
        self._check_sample_time()
        from .continuous import _as_matrix
        self._A = _as_matrix(self.params["A"])
        n = self._A.shape[0]
        self._B = _as_matrix(self.params["B"]).reshape(n, -1)
        self._C = _as_matrix(self.params["C"]).reshape(-1, n)
        self._D = _as_matrix(self.params["D"]).reshape(
            self._C.shape[0], self._B.shape[1])

    @property
    def n_dstates(self) -> int:
        return int(self._A.shape[0]) + int(self._C.shape[0])

    def initial_discrete_state(self):
        n = int(self._A.shape[0])
        state = as_array(self.params["x0"], n) if n else np.zeros(0)
        return np.concatenate([state, np.zeros(int(self._C.shape[0]))])

    def output_widths(self, input_widths):
        return [int(self._C.shape[0])]

    def output(self, t, x, xd, u):
        n = int(self._A.shape[0])
        return [xd[n:].copy()]

    def update(self, t, x, xd, u):
        n = int(self._A.shape[0])
        state = xd[:n]
        uu = u[0] if u else np.zeros(self._B.shape[1])
        y = self._C @ state + self._D @ uu
        return np.concatenate([self._A @ state + self._B @ uu,
                               np.atleast_1d(y)])


@register
class RateTransition(_DiscreteBase):
    type_name = "RateTransition"
    category = _CAT
    description = "Resample between two rates without an algebraic loop."
    params_spec = (
        ParamSpec("sample_time", "Output sample time (s)", 0.1),
        ParamSpec("x0", "Initial output", 0.0),
    )

    def configure(self) -> None:
        self._check_sample_time()

    @property
    def n_dstates(self) -> int:
        return 1

    @property
    def direct_feedthrough(self) -> bool:
        return False

    def initial_discrete_state(self):
        return np.array([float(self.params["x0"])])

    def output(self, t, x, xd, u):
        return [xd.copy()]

    def update(self, t, x, xd, u):
        return np.atleast_1d(u[0])[:1].astype(float) if u else xd

    def label(self):
        return f"rate\n{self.params['sample_time']:g}s"


@register
class Memory(_DiscreteBase):
    """
    The input one sample ago.

    Unlike a Unit Delay, whose held output is what it last sampled, Memory
    outputs the sample *before* that: at hit k it shows u(k−1). Simulink's
    Memory inherits its rate; Evans needs the sample time stated.
    """

    type_name = "Memory"
    category = _CAT
    description = "The input from the previous sample: y(k) = u(k−1)."
    params_spec = (
        ParamSpec("sample_time", "Sample time (s)", 0.1),
        ParamSpec("x0", "Initial output", 0.0),
    )

    def configure(self) -> None:
        self._check_sample_time()

    @property
    def n_dstates(self) -> int:
        return 2                            # [previous input, held output]

    def initial_discrete_state(self):
        x0 = float(self.params["x0"])
        return np.array([x0, x0])

    def output(self, t, x, xd, u):
        return [xd[1:2].copy()]

    def update(self, t, x, xd, u):
        uu = float(np.atleast_1d(u[0])[0]) if u else 0.0
        return np.array([uu, xd[0]])

    def label(self):
        return "Memory"


@register
class DiscreteIntegrator(_DiscreteBase):
    """
    K·T·Σu, by Simulink's three methods, with ``x(0)`` the initial condition:

    * Forward Euler:  ``y(k) = x(k)``,          ``x(k+1) = y(k) + K·T·u(k)``
    * Backward Euler: ``y(k) = x(k) + K·T·u(k)``, ``x(k+1) = y(k)``
    * Trapezoidal:    ``y(k) = x(k) + K·T/2·u(k)``, ``x(k+1) = y(k) + K·T/2·u(k)``

    With limits, the output and the state are both clamped, so the
    integrator does not wind up past them.
    """

    type_name = "DiscreteIntegrator"
    category = _CAT
    description = "K·T/(z−1) and its kin: forward, backward or trapezoidal."
    params_spec = (
        ParamSpec("gain", "Gain K", 1.0),
        ParamSpec("method", "Method", "Forward Euler", kind="choice",
                  choices=("Forward Euler", "Backward Euler", "Trapezoidal")),
        ParamSpec("sample_time", "Sample time (s)", 0.1),
        ParamSpec("x0", "Initial condition", 0.0),
        ParamSpec("limit", "Limit output", False, kind="bool"),
        ParamSpec("upper", "Upper limit", 1.0),
        ParamSpec("lower", "Lower limit", -1.0),
    )

    def configure(self) -> None:
        self._check_sample_time()
        if self.params["limit"] and self.params["upper"] <= self.params["lower"]:
            raise BlockError(
                f"DiscreteIntegrator {self.block_id!r}: the upper limit must "
                f"exceed the lower")

    @property
    def n_dstates(self) -> int:
        return 2                            # [x, held output]

    def initial_discrete_state(self):
        x0 = float(self.params["x0"])
        return np.array([x0, x0])

    def _clamp(self, v: float) -> float:
        if not self.params["limit"]:
            return v
        return float(np.clip(v, self.params["lower"], self.params["upper"]))

    def output(self, t, x, xd, u):
        return [xd[1:2].copy()]

    def update(self, t, x, xd, u):
        uu = float(np.atleast_1d(u[0])[0]) if u else 0.0
        kt = float(self.params["gain"]) * self.sample_time
        a, b = {"Forward Euler": (0.0, kt), "Backward Euler": (kt, 0.0),
                "Trapezoidal": (kt / 2, kt / 2)}[self.params["method"]]
        y = self._clamp(xd[0] + a * uu)
        return np.array([self._clamp(y + b * uu), y])

    def label(self):
        return f"KTs/(z−1)\nTs={self.params['sample_time']:g}"


@register
class DiscreteFIR(_DiscreteBase):
    type_name = "DiscreteFIR"
    category = _CAT
    description = "y(k) = Σ b_i·u(k−i): a finite impulse response filter."
    params_spec = (
        ParamSpec("coefficients", "Coefficients", "0.5, 0.5", kind="vector",
                  help="b0, b1, …: b0 multiplies the newest sample."),
        ParamSpec("sample_time", "Sample time (s)", 0.1),
    )

    def configure(self) -> None:
        self._check_sample_time()
        self._b = _parse_vector(self.params["coefficients"])

    @property
    def n_dstates(self) -> int:
        # The last len(b) − 1 inputs, newest first, then the held output.
        return len(self._b)

    def output_widths(self, input_widths):
        return [1]

    def output(self, t, x, xd, u):
        return [xd[-1:].copy()]

    def update(self, t, x, xd, u):
        uu = float(np.atleast_1d(u[0])[0]) if u else 0.0
        history = np.concatenate([[uu], xd[:-1]])
        y = float(self._b @ history)
        return np.concatenate([history[:-1], [y]])

    def label(self):
        return f"FIR\n{len(self._b)} taps"


@register
class DiscreteFilter(DiscreteTransferFcn):
    """
    num(z⁻¹)/den(z⁻¹): coefficients in ascending powers of z⁻¹, as signal
    processing writes them (``[1 -0.5]`` is ``1 − 0.5 z⁻¹``). Padding both
    to one length makes them the same numbers in descending powers of z.
    """

    type_name = "DiscreteFilter"
    category = _CAT
    description = "num(z⁻¹)/den(z⁻¹), coefficients in powers of z⁻¹."
    params_spec = (
        ParamSpec("num", "Numerator (z⁻¹)", "1", kind="vector"),
        ParamSpec("den", "Denominator (z⁻¹)", "1, -0.5", kind="vector"),
        ParamSpec("sample_time", "Sample time (s)", 0.1),
    )

    def configure(self) -> None:
        num = _parse_vector(self.params["num"])
        den = _parse_vector(self.params["den"])
        if den[0] == 0:
            raise BlockError(
                f"DiscreteFilter {self.block_id!r}: the denominator's first "
                f"coefficient must not be zero")
        n = max(len(num), len(den))
        padded = dict(self.params)
        self.params = {**padded,
                       "num": np.pad(num, (0, n - len(num))),
                       "den": np.pad(den, (0, n - len(den)))}
        try:
            super().configure()
        finally:
            self.params = padded

    def label(self):
        return f"H(z⁻¹)\nTs={self.params['sample_time']:g}"


@register
class Counter(_DiscreteBase):
    """Counts samples: 0, 1, …, upper, 0, 1, … (Counter Limited)."""

    type_name = "Counter"
    category = _CAT
    description = "Counts up once a sample and wraps after the upper limit."
    default_inputs = ()
    params_spec = (
        ParamSpec("upper", "Upper limit", 7, kind="int"),
        ParamSpec("sample_time", "Sample time (s)", 0.1),
    )

    def configure(self) -> None:
        self._check_sample_time()
        if int(self.params["upper"]) < 0:
            raise BlockError("Counter's upper limit cannot be negative")

    @property
    def n_dstates(self) -> int:
        return 2                            # [next count, held output]

    def initial_discrete_state(self):
        return np.zeros(2)

    def output(self, t, x, xd, u):
        return [xd[1:2].copy()]

    def update(self, t, x, xd, u):
        count = xd[0]
        following = 0.0 if count >= int(self.params["upper"]) else count + 1
        return np.array([following, count])

    def label(self):
        return f"count\n0…{self.params['upper']}"
