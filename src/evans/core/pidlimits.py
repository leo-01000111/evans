"""
PID tuning from limits — "overshoot under 10 %, settling under 2 s, …".
=======================================================================

The slider tuner (:mod:`evans.core.pidtune`) turns two numbers into gains in
closed form. This module answers the other question people ask: *I know what
the step response must satisfy; find gains that do it.*

The user states some of these limits (every one optional):

    overshoot      ≤ Mp %          (closed-loop step response)
    rise time      ≤ tr s          (10 → 90 %)
    settling time  ≤ ts s          (±2 %)
    DC error       ≤ e %           (|1 − y∞| for a unit step)
    phase margin   ≥ PM °
    gain margin    ≥ GM dB

and the search looks for ``Kp, Ki, Kd`` of the chosen controller type.

How it searches
---------------
The step metrics are not smooth in the gains (a settling time jumps when a
ripple leaves the band), so a gradient method would stall. Instead:

1. **Seeds.** A grid of loop-shaping designs (:func:`~evans.core.pidtune.tune`)
   over crossover and phase margin. They are stable and well-conditioned, so
   most limits are nearly met before any search starts.
2. **Cost.** Each limit contributes its *normalised* violation
   ``max(0, (value − limit)/scale)``; an unstable loop costs a large constant
   plus how far its worst pole is in the right half-plane. Meeting every limit
   costs zero from the violations, and a small secondary term (settling time
   relative to its own scale) then prefers the quicker of two feasible designs.
3. **Polish.** Nelder–Mead on the cheapest seeds, in log-gain coordinates so
   gains stay positive and a decade costs the same everywhere.

The result says, for each limit, what was asked and what was achieved, so a
limit that cannot be met (they can contradict each other, or the plant) shows
as such instead of returning gains that quietly fail.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import control as ctl
import numpy as np
from scipy.optimize import minimize

from .freqresp import bode
from .pidtune import (
    NEUTRAL_PHASE,
    PIDKind,
    TuneResult,
    _finish,
    _unity,
    default_crossover,
    reference_to_output,
    tune,
)
from .timeresp import _auto_tspan, compute_step_metrics, step_response
from .tuning import PIDParams, pid_tf

#: Samples of the step response while searching (the report uses 2000, as the
#: Time tab does).
SEARCH_POINTS = 400
#: Added to the cost of an unstable loop, so every stable design beats it.
UNSTABLE_COST = 1.0e3
#: Weight of the secondary "be quick" term next to the violations.
SPEED_WEIGHT = 1.0e-3
#: Seed grid: phase margins and crossover speeds tried before the polish.
SEED_PMS = (45.0, 60.0, 75.0)
SEED_SPEEDS = (-1.0, -0.5, 0.0, 0.5, 1.0)
#: How many of the cheapest seeds are polished, and the budget for each.
POLISH_SEEDS = 2
POLISH_EVALS = 100

#: The kinds of limit, in display order: key → (label, unit, direction).
#: Direction is ``"max"`` (value must stay ≤ limit) or ``"min"`` (≥ limit).
LIMIT_KINDS: dict[str, tuple[str, str, str]] = {
    "overshoot": ("Overshoot", "%", "max"),
    "rise": ("Rise time (10–90 %)", "s", "max"),
    "settling": ("Settling time", "s", "max"),
    "dc_error": ("DC error", "%", "max"),
    "phase_margin": ("Phase margin", "°", "min"),
    "gain_margin": ("Gain margin", "dB", "min"),
}


@dataclass(frozen=True)
class LimitCheck:
    """One limit against what the tuned loop achieves."""

    key: str
    label: str
    unit: str
    direction: str            # "max" or "min"
    limit: float
    value: float              # NaN when the loop could not be measured
    met: bool

    def describe(self) -> str:
        sign = "≤" if self.direction == "max" else "≥"
        mark = "✓" if self.met else "✗"
        value = "n/a" if not math.isfinite(self.value) else f"{self.value:.4g}"
        return (f"{mark} {self.label}: {value} {self.unit} "
                f"(limit {sign} {self.limit:g} {self.unit})")


@dataclass
class LimitsResult:
    """What the search found: gains, the loop they make, and the report."""

    tune: TuneResult
    checks: list[LimitCheck] = field(default_factory=list)
    evaluations: int = 0

    @property
    def met(self) -> bool:
        """Every stated limit is met and the loop is stable."""
        return self.tune.feasible and self.tune.stable \
            and all(c.met for c in self.checks)

    def describe(self) -> str:
        head = ("All limits met." if self.met
                else "Not every limit could be met; this is the closest "
                     "design found.")
        return "\n".join([head, *(c.describe() for c in self.checks)])


# ──────────────────────────────────────────────────────────────
#  Measuring a candidate
# ──────────────────────────────────────────────────────────────

def measure(C: ctl.TransferFunction, G: ctl.TransferFunction,
            H: ctl.TransferFunction, K1: ctl.TransferFunction,
            points: int = 2000, band: float = 0.02) -> dict[str, float]:
    """
    The six measured values for controller ``C`` in the loop ``K₁·C·G/(1+C·G·H)``.

    Unmeasurable values are NaN. An unstable closed loop returns only the key
    ``"unstable"`` (the worst pole's real part) — there is no step response to
    speak of.
    """
    L = C * G * H
    poles = np.atleast_1d(ctl.poles(ctl.feedback(L, 1)))
    if not len(poles):
        return {"unstable": 1.0}
    worst = float(np.max(poles.real))
    if worst >= -1e-9:
        return {"unstable": max(worst, 0.0) + 1e-3}

    out = dict.fromkeys(LIMIT_KINDS, float("nan"))
    try:
        bd = bode(L)
        out["phase_margin"] = float(bd.pm_deg)
        out["gain_margin"] = float(bd.gm_dB)
    except Exception:                                       # noqa: BLE001
        pass
    try:
        T = reference_to_output(C, G, H, K1)
        m = compute_step_metrics(step_response(T, t=_auto_tspan(T, points)))
    except Exception:                                       # noqa: BLE001
        return out
    out["overshoot"] = float(m.Mp_pct) if math.isfinite(m.Mp_pct) else 0.0
    rise = m.tr_1090 if math.isfinite(m.tr_1090) else m.tr_0100
    out["rise"] = float(rise)
    out["settling"] = float(m.ts_5pct if band >= 0.05 else m.ts_2pct)
    out["dc_error"] = abs(float(m.steady_state_error)) * 100.0
    return out


def _violation(key: str, value: float, limit: float) -> float:
    """Normalised amount by which ``value`` misses ``limit`` (0 when met)."""
    direction = LIMIT_KINDS[key][2]
    if not math.isfinite(value):
        # A missing gain margin means "infinite", which satisfies a minimum;
        # anything else that could not be measured is a miss.
        return 0.0 if key == "gain_margin" else 1.0
    scale = max(abs(limit), 1.0 if key in ("overshoot", "dc_error") else 1e-9)
    miss = value - limit if direction == "max" else limit - value
    return max(0.0, miss / scale)


def _met(key: str, value: float, limit: float) -> bool:
    return _violation(key, value, limit) <= 1e-6


# ──────────────────────────────────────────────────────────────
#  The search
# ──────────────────────────────────────────────────────────────

def _free(kind: PIDKind) -> tuple[bool, bool, bool]:
    """Which of Kp, Ki, Kd the controller type uses."""
    return (True, kind in (PIDKind.PI, PIDKind.PID),
            kind in (PIDKind.PD, PIDKind.PID))


class _Problem:
    """The cost function for one plant, controller type and set of limits."""

    def __init__(self, G, H, K1, kind: PIDKind, Tf: float,
                 limits: dict[str, float], band: float = 0.02) -> None:
        self.band = band
        self.G, self.H, self.K1 = G, H, K1
        self.kind, self.Tf, self.limits = kind, Tf, limits
        self.evals = 0
        self.best: tuple[float, PIDParams] | None = None

    def params(self, x: np.ndarray, signs: np.ndarray) -> PIDParams:
        free = _free(self.kind)
        gains, i = [0.0, 0.0, 0.0], 0
        for slot in range(3):
            if free[slot]:
                gains[slot] = float(signs[slot] * math.exp(x[i]))
                i += 1
        return PIDParams(Kp=gains[0], Ki=gains[1], Kd=gains[2],
                         Tf=self.Tf if free[2] else 0.0)

    def cost_of(self, params: PIDParams) -> float:
        self.evals += 1
        try:
            values = measure(pid_tf(params), self.G, self.H, self.K1,
                             SEARCH_POINTS, self.band)
        except Exception:                                   # noqa: BLE001
            return UNSTABLE_COST * 10.0
        if "unstable" in values:
            cost = UNSTABLE_COST + values["unstable"]
        else:
            cost = sum(_violation(k, values[k], lim)
                       for k, lim in self.limits.items())
            ts = values["settling"]
            cost += SPEED_WEIGHT * (math.log1p(ts) if math.isfinite(ts)
                                    else 10.0)
        if self.best is None or cost < self.best[0]:
            self.best = (cost, params)
        return cost


def _signs(params: PIDParams) -> np.ndarray:
    return np.array([1.0 if p >= 0 else -1.0
                     for p in (params.Kp, params.Ki, params.Kd)])


def _log_vector(params: PIDParams, kind: PIDKind) -> np.ndarray:
    gains = (params.Kp, params.Ki, params.Kd)
    free = _free(kind)
    return np.array([math.log(max(abs(g), 1e-12))
                     for g, f in zip(gains, free) if f])


def tune_to_limits(G: ctl.TransferFunction,
                   kind: PIDKind | str = PIDKind.PID,
                   limits: dict[str, float] | None = None,
                   Tf: float = 0.0,
                   sensor: ctl.TransferFunction | None = None,
                   feedforward: ctl.TransferFunction | None = None,
                   settling_band: float = 0.02) -> LimitsResult:
    """
    Find ``kind`` gains for ``G`` that meet ``limits``.

    ``limits`` maps keys of :data:`LIMIT_KINDS` to numbers; keys left out are
    not constrained. ``sensor`` (H) and ``feedforward`` (K₁) place the
    controller in the course loop, as for :func:`~evans.core.pidtune.tune`.

    ``settling_band`` is the fraction the settling time is measured to:
    0.02 (the default) or 0.05.

    With no limits at all the answer is the balanced slider design.
    """
    kind = PIDKind(kind)
    limits = {k: float(v) for k, v in (limits or {}).items()}
    for key in limits:
        if key not in LIMIT_KINDS:
            raise ValueError(f"unknown limit {key!r}; "
                             f"choose from {', '.join(LIMIT_KINDS)}")
    H = sensor if sensor is not None else _unity()
    K1 = feedforward if feedforward is not None else _unity()
    seen = G * H
    if settling_band not in (0.02, 0.05):
        raise ValueError("settling_band must be 0.02 or 0.05")
    problem = _Problem(G, H, K1, kind, Tf, limits, settling_band)

    seeds = _seeds(seen, kind, Tf)
    if not seeds:
        seeds = [PIDParams(Kp=1.0, Ki=0.1 if _free(kind)[1] else 0.0,
                           Kd=0.1 if _free(kind)[2] else 0.0,
                           Tf=Tf if _free(kind)[2] else 0.0)]
    scored = sorted(((problem.cost_of(p), i, p)
                     for i, p in enumerate(seeds)), key=lambda s: s[:2])

    if limits:
        for _cost, _i, seed in scored[:POLISH_SEEDS]:  # noqa: B007
            if problem.best is not None and problem.best[0] <= 0.0 \
                    and not limits:
                break
            signs = _signs(seed)
            x0 = _log_vector(seed, kind)
            minimize(lambda x, s=signs: problem.cost_of(problem.params(x, s)),
                     x0, method="Nelder-Mead",
                     options={"maxfev": POLISH_EVALS, "xatol": 1e-3,
                              "fatol": 1e-6})

    assert problem.best is not None
    params = problem.best[1]
    return _report(params, kind, G, H, K1, limits, problem.evals,
                   settling_band)


def _seeds(G: ctl.TransferFunction, kind: PIDKind, Tf: float
           ) -> list[PIDParams]:
    """Loop-shaping designs over a small grid of crossover and margin."""
    seeds: list[PIDParams] = []
    for pm in SEED_PMS:
        try:
            neutral = default_crossover(G, pm, NEUTRAL_PHASE[kind.value])
        except Exception:                                   # noqa: BLE001
            continue
        for speed in SEED_SPEEDS:
            try:
                result = tune(G, kind, wc=float(neutral * 10.0 ** speed),
                              pm_deg=pm, Tf=Tf)
            except Exception:                               # noqa: BLE001
                continue
            if result.feasible:
                seeds.append(result.params)
    return seeds


def _report(params: PIDParams, kind: PIDKind, G, H, K1,
            limits: dict[str, float], evals: int,
            band: float) -> LimitsResult:
    bd = bode(pid_tf(params) * G * H)
    tuned = _finish(kind, params, G, H, K1, bd.wc, bd.pm_deg, float("nan"))
    values = measure(tuned.C, G, H, K1, band=band)
    checks = []
    for key, limit in limits.items():
        label, unit, direction = LIMIT_KINDS[key]
        if key == "settling":
            label = f"{label} (±{band * 100:g} %)"
        value = values.get(key, float("nan"))
        checks.append(LimitCheck(key, label, unit, direction, limit, value,
                                 _met(key, value, limit) and
                                 "unstable" not in values))
    return LimitsResult(tune=tuned, checks=checks, evaluations=evals)


# ──────────────────────────────────────────────────────────────
#  The limits as zones on the step-response plot
# ──────────────────────────────────────────────────────────────

#: Stand-in for "to the edge of the plot" in a zone.
EDGE = 1.0e6


@dataclass(frozen=True)
class Zone:
    """
    A rectangle of the step plot the response must stay out of.

    Times and values are for a unit step. ``±EDGE`` means "to the edge".
    ``at_end`` puts the zone's left side at the end of the plotted time
    instead of ``t0`` (the DC-error limit is about the final value).
    """

    key: str            # the limit it draws, a key of LIMIT_KINDS
    t0: float
    t1: float
    y0: float
    y1: float
    label: str
    at_end: bool = False


def crossing_time(t: np.ndarray, y: np.ndarray, level: float) -> float | None:
    """First time the response reaches ``level`` from below (interpolated)."""
    above = np.flatnonzero(y >= level)
    if not len(above):
        return None
    i = int(above[0])
    if i == 0:
        return float(t[0])
    frac = (level - y[i - 1]) / (y[i] - y[i - 1])
    return float(t[i - 1] + frac * (t[i] - t[i - 1]))


def limit_zones(limits: dict[str, float], band: float = 0.02,
                t10: float = 0.0) -> list[Zone]:
    """
    The zones the step response must avoid, one or two per time-domain limit.

    * overshoot ``Mp``: everything above ``1 + Mp/100``, all along the time axis;
    * settling ``ts``: from ``ts`` on, everything outside ``1 ± band`` — two
      blocks, above and below, with the band itself left open;
    * rise ``tr``: everything below 0.9 from ``t10 + tr`` on, where ``t10`` is
      when the response passes 10 % (pass the current design's, or 0);
    * DC error ``e``: at the far right, everything outside ``1 ± e/100``.

    The two margins have no place on a step plot and give no zone.
    """
    zones: list[Zone] = []
    if "overshoot" in limits:
        mp = limits["overshoot"]
        zones.append(Zone("overshoot", 0.0, EDGE, 1.0 + mp / 100.0, EDGE,
                          f"overshoot > {mp:g} %"))
    if "rise" in limits:
        t0 = t10 + limits["rise"]
        zones.append(Zone("rise", t0, EDGE, -EDGE, 0.9,
                          f"below 90 % after {t0:.3g} s"))
    if "settling" in limits:
        ts = limits["settling"]
        pct = f"{band * 100:g} %"
        zones.append(Zone("settling", ts, EDGE, 1.0 + band, EDGE,
                          f"outside ±{pct} after {ts:g} s"))
        zones.append(Zone("settling", ts, EDGE, -EDGE, 1.0 - band, ""))
    if "dc_error" in limits:
        e = limits["dc_error"] / 100.0
        zones.append(Zone("dc_error", 0.0, EDGE, 1.0 + e, EDGE,
                          f"DC error > {limits['dc_error']:g} %", at_end=True))
        zones.append(Zone("dc_error", 0.0, EDGE, -EDGE, 1.0 - e, "",
                          at_end=True))
    return zones
