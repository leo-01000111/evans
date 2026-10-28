"""
Fitting, optimisation and integration.
======================================
Least squares, minimisation, linear and quadratic programming, quadrature, curve fits.

A mixin of :class:`.matlab_runtime._Library`: each ``f_<name>`` method is
the MATLAB function ``<name>``. It is imported by :mod:`.matlab_runtime`
just before ``_Library`` is defined, so the helpers above that line can be
imported from it by name; anything defined further down is reached through
the module (``_mr._sprintf``) at call time. Import :mod:`.matlab_runtime` first, never this module on
its own: the two import each other.

Conventions
-----------
* ``x`` comes back shaped like ``x0`` (a scalar for a scalar ``x0``); the
  handle is called with an argument of that shape.
* The solvers print MATLAB's short exit message (``Local minimum found.``)
  unless ``Display`` is ``'off'``; ``'iter'`` is treated as ``'final'``.
* Tolerances default tighter than MATLAB's, so answers sit at least as close
  to the true optimum as MATLAB's do. Options that only steer the path
  (``Algorithm``, finite-difference settings, Hessian hints) are accepted;
  callbacks (``OutputFcn``, ``PlotFcn``) are refused.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np

from . import matlab_runtime as _mr  # noqa: F401
from .matlab_runtime import (
    Cell,
    MatlabError,
    Struct,
    _is_function,
    _nargout,
    _normalise,
    _numel,
    _scalar,
    _shape,
)

_EPS = np.finfo(float).eps

# ──────────────────────────────────────────────────────────────
#  Small helpers
# ──────────────────────────────────────────────────────────────


def _empty(x) -> bool:
    return x is None or (not isinstance(x, str) and _numel(x) == 0)


def _vec(x, n=None, name="argument"):
    """A float vector, or None for ``[]``."""
    if _empty(x):
        return None
    v = np.asarray(x, dtype=float).reshape(-1)
    if n is not None and v.size != n:
        raise MatlabError(f"{name} must have {n} elements, one per "
                          f"variable (it has {v.size}).")
    return v


def _mat(x, n, name):
    if _empty(x):
        return None
    a = np.asarray(x, dtype=float)
    if a.ndim < 2:
        a = a.reshape(1, -1)
    if a.shape[1] != n:
        raise MatlabError(f"{name} must have {n} columns, one per variable.")
    return a


def _column(v):
    v = np.asarray(v, float).reshape(-1)
    return _scalar(float(v[0])) if v.size == 1 else v.reshape(-1, 1)


def _shaped(v, shape):
    """The solver's flat vector, shaped like ``x0``."""
    v = np.asarray(v, float).reshape(-1)
    if v.size == 1:
        return _scalar(float(v[0]))
    return v.reshape(shape).copy()


def _real_out(out, who):
    a = np.asarray(out)
    if np.iscomplexobj(a):
        if np.any(np.imag(a) != 0):
            raise MatlabError(f"{who} cannot continue: the function "
                              "returned complex values.")
        a = a.real
    if a.dtype == object:
        raise MatlabError(f"{who} cannot continue: the function must "
                          "return numbers.")
    return a.astype(float)


def _central_grad(fn, v):
    """Central-difference gradient of a scalar function of a flat vector."""
    g = np.zeros(v.size)
    for i in range(v.size):
        h = _EPS ** (1 / 3) * max(1.0, abs(v[i]))
        e = np.zeros(v.size)
        e[i] = h
        g[i] = (fn(v + e) - fn(v - e)) / (2 * h)
    return g


def _central_jac(fn, v):
    """Central-difference Jacobian (m×n) of a vector function."""
    cols = []
    for i in range(v.size):
        h = _EPS ** (1 / 3) * max(1.0, abs(v[i]))
        e = np.zeros(v.size)
        e[i] = h
        cols.append((np.asarray(fn(v + e)) - np.asarray(fn(v - e))) / (2 * h))
    return np.column_stack(cols) if cols else np.zeros((0, 0))


def _bounds(lb, ub, n):
    lo = _vec(lb, n, "lb")
    hi = _vec(ub, n, "ub")
    lo = np.full(n, -np.inf) if lo is None else lo
    hi = np.full(n, np.inf) if hi is None else hi
    if np.any(lo > hi):
        raise MatlabError("Exiting due to infeasibility: at least one lower "
                          "bound exceeds the corresponding upper bound.")
    return lo, hi


# Option names, MATLAB's current names first then the optimset ones.
_ALIASES = {
    "tolx": ("StepTolerance", "TolX"),
    "tolfun": ("FunctionTolerance", "TolFun"),
    "tolopt": ("OptimalityTolerance", "TolFun"),
    "tolcon": ("ConstraintTolerance", "TolCon"),
    "maxiter": ("MaxIterations", "MaxIter"),
    "maxfev": ("MaxFunctionEvaluations", "MaxFunEvals"),
    "display": ("Display",),
    "algorithm": ("Algorithm",),
    "gradient": ("SpecifyObjectiveGradient", "GradObj", "Jacobian"),
    "relgap": ("RelativeGapTolerance", "TolGapRel"),
}

#: Every option ``optimoptions`` takes. Those that only steer the path are
#: accepted and do not change the answer.
_KNOWN = {
    "Algorithm", "Display", "StepTolerance", "TolX", "FunctionTolerance",
    "TolFun", "OptimalityTolerance", "ConstraintTolerance", "TolCon",
    "MaxIterations", "MaxIter", "MaxFunctionEvaluations", "MaxFunEvals",
    "SpecifyObjectiveGradient", "GradObj", "Jacobian",
    "SpecifyConstraintGradient", "GradConstr", "FiniteDifferenceType",
    "FiniteDifferenceStepSize", "TypicalX", "HessianApproximation",
    "HessianFcn", "Hessian", "SubproblemAlgorithm", "ScaleProblem",
    "CheckGradients", "UseParallel", "Diagnostics", "MaxPCGIter",
    "RelativeGapTolerance", "AbsoluteGapTolerance", "IntegerTolerance",
    "MaxTime", "OutputFcn", "PlotFcn", "PlotFcns",
}

_SOLVERS = ("fmincon", "fminunc", "fsolve", "lsqcurvefit", "lsqnonlin",
            "linprog", "intlinprog", "quadprog", "fzero", "fminbnd")


def _truthy(v) -> bool:
    if isinstance(v, str):
        return v.lower() in ("on", "true")
    try:
        return bool(_scalar(v))
    except (TypeError, ValueError):
        return False


class OptimOptions(Struct):
    """What ``optimoptions`` returns: a struct of the options set."""

    def __repr__(self) -> str:
        solver = self.get("SolverName", "")
        shown = {k: v for k, v in self.items() if k != "SolverName"}
        lines = [f"  {solver} options:", ""]
        if not shown:
            lines.append("   (all options at their defaults)")
            return "\n".join(lines)
        lines.append("   Set properties:")
        width = max(len(k) for k in shown)
        lines += [f"    {k:>{width}}: {_mr._brief(v)}" for k, v in shown.items()]
        return "\n".join(lines)


# ──────────────────────────────────────────────────────────────
#  Gauss–Kronrod 7–15, the rule MATLAB's integral and quadgk use
# ──────────────────────────────────────────────────────────────

_XK_HALF = np.array([0.991455371120812639206854697526329,
                     0.949107912342758524526189684047851,
                     0.864864423359769072789712788640926,
                     0.741531185599394439863864773280788,
                     0.586087235467691130294144845693013,
                     0.405845151377397166906606412076961,
                     0.207784955007898467600689403773245])
_WK_HALF = np.array([0.022935322010529224963732008058970,
                     0.063092092629978553290700663189204,
                     0.104790010322250183839876322541518,
                     0.140653259715525918745189590510238,
                     0.169004726639267902826583426598550,
                     0.190350578064785409913256402421014,
                     0.204432940075298892414161999234649])
_WK0 = 0.209482141084727828012999174891714
_WG_HALF = np.array([0.129484966168869693270611432679082,
                     0.279705391489276667901467771423780,
                     0.381830050505118944950369775488975])
_WG0 = 0.417959183673469387755102040816327

_XK = np.concatenate([-_XK_HALF, [0.0], _XK_HALF[::-1]])
_WK = np.concatenate([_WK_HALF, [_WK0], _WK_HALF[::-1]])
_WG = np.zeros(15)
_WG[[1, 3, 5]] = _WG_HALF
_WG[7] = _WG0
_WG[[13, 11, 9]] = _WG_HALF


def _path(a, b, t):
    """
    Map ``t`` in [-1, 1] onto [a, b]: ``x`` and ``dx/dt``. A finite interval
    uses quadgk's ``x = (b-a)/4·t(3-t²) + (b+a)/2``, which weakens endpoint
    singularities; a half-infinite one ``x = a + (u/(1-u))²``; the whole
    line ``x = t/(1-t²)``. ``a`` and ``b`` may be arrays (one per batch row).
    """
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    sign = np.where(a > b, -1.0, 1.0)
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    flo, fhi = np.isfinite(lo), np.isfinite(hi)
    with np.errstate(all="ignore"):
        x1 = (hi - lo) / 4 * t * (3 - t * t) + (hi + lo) / 2
        w1 = 3 * (hi - lo) / 4 * (1 - t * t)
        u = (t + 1) / 2
        x2 = lo + (u / (1 - u)) ** 2
        w2 = u / (1 - u) ** 3
        v = (1 - t) / 2
        x3 = hi - (v / (1 - v)) ** 2
        w3 = v / (1 - v) ** 3
        x4 = t / (1 - t * t)
        w4 = (1 + t * t) / (1 - t * t) ** 2
    x = np.where(flo & fhi, x1, np.where(flo, x2, np.where(fhi, x3, x4)))
    w = np.where(flo & fhi, w1, np.where(flo, w2, np.where(fhi, w3, w4)))
    return x, w * sign


def _gk_adapt(g, abstol, reltol, maxint=650, who="integral"):
    """
    Adaptive Gauss–Kronrod over t in [-1, 1], as quadgk: ten starting
    subintervals, an interval retired once its error is within its share
    of ``max(AbsTol, RelTol·|Q|)``, the rest halved. ``g(t)`` returns the
    weighted integrand with the nodes on the last axis; any leading axes
    are a batch, all brought to tolerance together.
    """
    lo = np.linspace(-1, 1, 11)[:-1]
    hi = np.linspace(-1, 1, 11)[1:]
    q_ok = 0.0
    e_ok = 0.0
    while True:
        mid, half = (lo + hi) / 2, (hi - lo) / 2
        t = (mid[:, None] + half[:, None] * _XK).reshape(-1)
        y = np.asarray(g(t))
        y = y.reshape(y.shape[:-1] + (lo.size, 15))
        qk = (y @ _WK) * half
        qg = (y @ _WG) * half
        err = np.abs(qk - qg)
        Q = q_ok + qk.sum(-1)
        E = e_ok + err.sum(-1)
        if not np.all(np.isfinite(Q)):
            print("Warning: Infinite or Not-a-Number value encountered.")
            return Q, np.full(np.shape(Q), np.inf)
        tol = np.maximum(abstol, reltol * np.abs(Q))
        if np.all(E <= tol):
            return Q, E
        done = err <= (np.asarray(tol)[..., None] * half)
        if done.ndim > 1:
            done = np.all(done, axis=tuple(range(done.ndim - 1)))
        q_ok = q_ok + qk[..., done].sum(-1)
        e_ok = e_ok + err[..., done].sum(-1)
        lo, hi, mid = lo[~done], hi[~done], mid[~done]
        if not lo.size:
            return Q, E
        if 2 * lo.size > maxint:
            print(f"Warning: Reached the limit on the maximum number of "
                  f"intervals in use. Approximate bound on error is "
                  f"{float(np.max(E)):9.1e}. The integral may not exist, or "
                  f"it may be difficult to approximate numerically to the "
                  f"requested accuracy.")
            return Q, E
        if np.min(hi - lo) < 100 * _EPS:
            print(f"Warning: Minimum step size reached near x = "
                  f"{float(mid[0]):g}. There may be a singularity, or the "
                  f"tolerances may be too tight for this problem.")
            return Q, E
        lo, hi = np.concatenate([lo, mid]), np.concatenate([mid, hi])


def _name_values(args, allowed, who):
    if len(args) % 2:
        raise MatlabError(f"{who}: options must come in Name, Value pairs.")
    out = {}
    for k in range(0, len(args), 2):
        name = args[k]
        if not isinstance(name, str):
            raise MatlabError(f"{who}: option names must be text.")
        match = next((a for a in allowed if a.lower() == name.lower()), None)
        if match is None:
            raise MatlabError(f"Invalid option '{name}' for {who}. Evans "
                              f"supports: {', '.join(allowed)}.")
        out[match] = args[k + 1]
    return out


# ──────────────────────────────────────────────────────────────
#  Curve fits: the library models
# ──────────────────────────────────────────────────────────────

def _poly_formula(n: int) -> str:
    terms = []
    for k in range(n + 1):
        power = n - k
        name = f"p{k + 1}"
        terms.append(name if power == 0 else f"{name}*x" if power == 1
                     else f"{name}*x^{power}")
    return " + ".join(terms)


_MODELS = {
    "exp1": (("a", "b"), "a*exp(b*x)",
             lambda p, x: p[0] * np.exp(p[1] * x)),
    "exp2": (("a", "b", "c", "d"), "a*exp(b*x) + c*exp(d*x)",
             lambda p, x: p[0] * np.exp(p[1] * x) + p[2] * np.exp(p[3] * x)),
    "power1": (("a", "b"), "a*x^b", lambda p, x: p[0] * x ** p[1]),
    "power2": (("a", "b", "c"), "a*x^b+c",
               lambda p, x: p[0] * x ** p[1] + p[2]),
    "sin1": (("a1", "b1", "c1"), "a1*sin(b1*x+c1)",
             lambda p, x: p[0] * np.sin(p[1] * x + p[2])),
    "gauss1": (("a1", "b1", "c1"), "a1*exp(-((x-b1)/c1)^2)",
               lambda p, x: p[0] * np.exp(-((x - p[1]) / p[2]) ** 2)),
}


def _model(name: str):
    """(kind, coefficient names, formula, evaluator, degree) for a name."""
    key = name.strip().lower()
    if key.startswith("poly") and key[4:].isdigit() and len(key) == 5:
        n = int(key[4:])
        if 1 <= n <= 9:
            names = tuple(f"p{k + 1}" for k in range(n + 1))
            return ("Linear", key, names, _poly_formula(n),
                    lambda p, x: np.polyval(p, x), n)
    if key in _MODELS:
        names, formula, fn = _MODELS[key]
        return ("General", key, names, formula, fn, None)
    raise MatlabError(
        f"Evans's fit supports the library models poly1 to poly9, exp1, "
        f"exp2, power1, power2, sin1 and gauss1; '{name}' is not one of "
        f"them (custom fittype expressions are not supported).")


def _linear_ls(B, y):
    """Least squares a = B\\y for the coefficients of a linear model."""
    return np.linalg.lstsq(B, y, rcond=None)[0]


def _start(key, x, y):
    """A starting point for a nonlinear library model, from the data."""
    span = max(float(np.ptp(x)), _EPS)
    if key in ("exp1", "power1"):
        s = 1.0 if np.sum(y > 0) >= np.sum(y < 0) else -1.0
        ok = (s * y > 0) & ((x > 0) if key == "power1" else True)
        if np.sum(ok) >= 2:
            xx = np.log(x[ok]) if key == "power1" else x[ok]
            b, la = np.polyfit(xx, np.log(s * y[ok]), 1)
            return np.array([s * math.exp(la), b])
        return np.array([float(np.mean(y)) or 1.0, 0.0])
    if key == "power2":
        best = None
        for b in np.linspace(-4, 4, 161):
            if abs(b) < 1e-9:
                continue
            B = np.column_stack([x ** b, np.ones_like(x)])
            a, c = _linear_ls(B, y)
            r = np.sum((B @ [a, c] - y) ** 2)
            if best is None or r < best[0]:
                best = (r, [a, b, c])
        return np.array(best[1])
    if key == "exp2":
        rates = np.linspace(-8, 8, 33) / span
        best = None
        for i, b in enumerate(rates):
            for d in rates[i + 1:]:
                B = np.column_stack([np.exp(b * x), np.exp(d * x)])
                a, c = _linear_ls(B, y)
                r = np.sum((B @ [a, c] - y) ** 2)
                if np.isfinite(r) and (best is None or r < best[0]):
                    best = (r, [a, b, c, d])
        return np.array(best[1])
    if key == "sin1":
        n = x.size
        top = math.pi * n / span
        best = None
        for b in np.linspace(top / (20 * n), top, 40 * n):
            B = np.column_stack([np.sin(b * x), np.cos(b * x)])
            al, be = _linear_ls(B, y)
            r = np.sum((B @ [al, be] - y) ** 2)
            if best is None or r < best[0]:
                best = (r, [math.hypot(al, be), b, math.atan2(be, al)])
        return np.array(best[1])
    if key == "gauss1":
        k = int(np.argmax(np.abs(y)))
        a = y[k]
        w = np.abs(y) / max(np.sum(np.abs(y)), _EPS)
        sd = math.sqrt(max(float(np.sum(w * (x - x[k]) ** 2)), _EPS))
        return np.array([a, x[k], math.sqrt(2) * sd])
    raise MatlabError(f"No start point for {key}.")


class cfit:  # noqa: N801  (MATLAB's class name; _brief shows it)
    """
    What ``fit`` returns: the model, its coefficients as fields, callable
    as ``f(x)``, displayed as MATLAB displays a cfit.
    """

    def __init__(self, kind, key, names, formula, fn, values, bounds):
        self._kind, self._key, self._names = kind, key, names
        self._formula, self._fn = formula, fn
        self._values = np.asarray(values, float)
        self._bounds = bounds           # 2×p, or None

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        if name in self._names:
            return _scalar(float(self._values[self._names.index(name)]))
        raise AttributeError(f"Unrecognized field name \"{name}\".")

    def __call__(self, *args):
        if len(args) != 1:
            raise MatlabError("Evaluate a fit at one array of points: f(x).")
        x = args[0]
        a = np.asarray(x, float)
        out = self._fn(self._values, a)
        return _scalar(float(out)) if np.ndim(out) == 0 else out

    def __repr__(self) -> str:
        title = self._key[0].upper() + self._key[1:]
        lines = [f" {self._kind} model {title}:",
                 f" f(x) = {self._formula}"]
        if self._bounds is None:
            lines.append(" Coefficients:")
        else:
            lines.append(" Coefficients (with 95% confidence bounds):")
        width = max(len(n) for n in self._names)
        for i, n in enumerate(self._names):
            line = f"   {n:>{width}} = {self._values[i]:>11.4g}"
            if self._bounds is not None:
                lo, hi = self._bounds[:, i]
                line += f"  ({lo:.4g}, {hi:.4g})"
            lines.append(line)
        return "\n".join(lines)


def _as_cfit(f, who):
    if not isinstance(f, cfit):
        raise MatlabError(f"{who} needs a fit returned by fit(x, y, ...).")
    return f


# ──────────────────────────────────────────────────────────────
#  The library
# ──────────────────────────────────────────────────────────────

class OptimLibrary:
    """lsqcurvefit, fmincon, integral, fit and the rest."""

    # ── options ─────────────────────────────────────────────────

    def f_optimoptions(self, solver, *pairs):
        """``optimoptions(solver, 'Name', value, ...)`` or ``(old, ...)``."""
        if isinstance(solver, Mapping):
            out = OptimOptions(solver)
        else:
            name = str(solver)
            if name not in _SOLVERS:
                raise MatlabError(f"Invalid solver specified. Evans's "
                                  f"optimoptions knows {', '.join(_SOLVERS)}.")
            out = OptimOptions(SolverName=name)
        if len(pairs) % 2:
            raise MatlabError("Options must come in Name, Value pairs.")
        for k in range(0, len(pairs), 2):
            key = str(pairs[k])
            match = next((n for n in _KNOWN if n.lower() == key.lower()), None)
            if match is None:
                raise MatlabError(f"'{key}' is not an option for "
                                  f"{out.get('SolverName', 'this solver')}.")
            out[match] = pairs[k + 1]
        return out

    def _op_opts(self, options, who):
        if options is not None and not isinstance(options, Mapping) \
                and not _empty(options):
            raise MatlabError(f"{who}: options must be made with "
                              "optimoptions or optimset.")
        for bad in ("OutputFcn", "PlotFcn", "PlotFcns"):
            if not _empty(self._option(options, bad, None)):
                raise MatlabError(f"{who}: Evans does not support the "
                                  f"{bad} option.")
        out = {}
        for key, names in _ALIASES.items():
            value = None
            for n in names:
                value = self._option(options, n, None)
                if value is not None:
                    break
            out[key] = value
        display = out["display"]
        out["quiet"] = isinstance(display, str) and display.lower() in (
            "off", "none", "iter-off")
        out["gradient"] = out["gradient"] is not None and _truthy(
            out["gradient"])
        return out

    @staticmethod
    def _op_num(o, key, default):
        v = o.get(key)
        return default if v is None else float(_scalar(v))

    @staticmethod
    def _op_say(o, text):
        if not o["quiet"]:
            print(text)

    def _op_fn(self, f, shape, who, nargout=1):
        """A flat-vector wrapper round a handle taking an x0-shaped arg."""
        def call(v):
            arg = float(v[0]) if v.size == 1 else v.reshape(shape).copy()
            out = self.rt.call(f, (arg,), nargout=nargout)
            return out
        return call

    @staticmethod
    def _op_refuse_problem(fun, who):
        if isinstance(fun, Mapping):
            raise MatlabError(f"Evans's {who} does not take a problem "
                              "structure; pass the arguments directly.")

    # ── least squares and equations ─────────────────────────────

    def _op_least_squares(self, who, residual, x0, lb, ub, options, jac_fn=None):
        from scipy.optimize import least_squares
        o = self._op_opts(options, who)
        start = np.asarray(x0, float).reshape(-1)
        n = start.size
        lo, hi = _bounds(lb, ub, n)
        bounded = np.any(np.isfinite(lo)) or np.any(np.isfinite(hi))
        if bounded:
            inset = 1e-10 * np.maximum(1, np.abs(start))
            start = np.clip(start, np.where(np.isfinite(lo), lo + inset, lo),
                            np.where(np.isfinite(hi), hi - inset, hi))
            start = np.where(lo == hi, lo, start)
        r0 = residual(start)
        m = r0.size
        algo = o["algorithm"]
        method = "lm" if (isinstance(algo, str) and algo.lower().startswith(
            "levenberg") and not bounded and m >= n) else "trf"
        kwargs = {"ftol": self._op_num(o, "tolfun", 1e-12),
                  "xtol": self._op_num(o, "tolx", 1e-12),
                  "gtol": self._op_num(o, "tolopt", 1e-12)}
        if o["maxfev"] is not None:
            kwargs["max_nfev"] = int(self._op_num(o, "maxfev", 0))
        if m < n and method == "lm":
            method = "trf"
        res = least_squares(residual, start, jac=jac_fn or (lambda v: _central_jac(residual, v)),
                            bounds=(lo, hi), method=method, **kwargs)
        flag = {1: 1, 2: 3, 3: 2, 4: 3, 0: 0}.get(res.status, -2)
        resnorm = float(np.sum(res.fun ** 2))
        messages = {
            1: "\nLocal minimum found.\n\nOptimization completed because the "
               "size of the gradient is less than\nthe value of the "
               "optimality tolerance.\n",
            2: f"\nLocal minimum possible.\n\n{who} stopped because the size "
               "of the current step is less than\nthe value of the step size "
               "tolerance.\n",
            3: f"\nLocal minimum possible.\n\n{who} stopped because the final "
               "change in the sum of squares relative to \nits initial value "
               "is less than the value of the function tolerance.\n",
            0: f"\nSolver stopped prematurely.\n\n{who} stopped because it "
               "exceeded the function evaluation limit.\n"}
        self._op_say(o, messages.get(flag, f"\n{who} stopped: {res.message}\n"))
        output = Struct(firstorderopt=float(np.max(np.abs(res.grad)))
                        if res.grad.size else 0.0,
                        iterations=int(res.nfev), funcCount=int(res.nfev),
                        algorithm="levenberg-marquardt" if method == "lm"
                        else "trust-region-reflective",
                        message=str(res.message))
        return res, resnorm, flag, output

    @_nargout
    def f_lsqcurvefit(self, fun, x0, xdata, ydata, lb=None, ub=None,
                      options=None, *rest, nargout=1):
        """``[x, resnorm, residual, exitflag, output] = lsqcurvefit(...)``."""
        self._op_refuse_problem(fun, "lsqcurvefit")
        if rest:
            raise MatlabError("Evans's lsqcurvefit takes lb and ub as its "
                              "only constraints (no A, b, Aeq, beq, nonlcon).")
        shape = np.shape(np.asarray(x0, float))
        yd = np.asarray(ydata, float)
        call = self._op_fn(lambda x: self.rt.call(fun, (x, xdata), nargout=1),
                        shape, "lsqcurvefit")
        o = self._op_opts(options, "lsqcurvefit")

        def residual(v):
            model = _real_out(call(v), "lsqcurvefit")
            if model.size != yd.size:
                raise MatlabError("Function value and YDATA sizes are not "
                                  "equal.")
            return (model.reshape(-1) - yd.reshape(-1))

        jac = None
        if o["gradient"]:
            def jac(v):
                arg = float(v[0]) if v.size == 1 else v.reshape(shape).copy()
                out = self.rt.call(fun, (arg, xdata), nargout=2)
                return np.atleast_2d(np.asarray(out[1], float))
        res, resnorm, flag, output = self._op_least_squares(
            "lsqcurvefit", residual, x0, lb, ub, options, jac)
        resid = res.fun.reshape(yd.shape) if yd.ndim else res.fun
        out = (_shaped(res.x, shape), resnorm,
               _normalise(np.asarray(resid)) if np.size(resid) > 1
               else _scalar(float(np.asarray(resid).reshape(-1)[0])),
               flag, output)
        if nargout > 5:
            raise MatlabError("Evans's lsqcurvefit returns at most five "
                              "outputs [x, resnorm, residual, exitflag, "
                              "output].")
        return out[:nargout] if nargout >= 2 else out[0]

    @_nargout
    def f_lsqnonlin(self, fun, x0, lb=None, ub=None, options=None, *rest,
                    nargout=1):
        """``[x, resnorm, residual, exitflag, output] = lsqnonlin(...)``."""
        self._op_refuse_problem(fun, "lsqnonlin")
        if rest:
            raise MatlabError("Evans's lsqnonlin takes lb and ub as its only "
                              "constraints (no A, b, Aeq, beq, nonlcon).")
        shape = np.shape(np.asarray(x0, float))
        call = self._op_fn(fun, shape, "lsqnonlin")
        o = self._op_opts(options, "lsqnonlin")
        out_shape = []

        def residual(v):
            r = _real_out(call(v), "lsqnonlin")
            if not out_shape:
                out_shape.append(r.shape)
            return r.reshape(-1)

        jac = None
        if o["gradient"]:
            jac = self._op_jacobian_fn(fun, shape)
        res, resnorm, flag, output = self._op_least_squares(
            "lsqnonlin", residual, x0, lb, ub, options, jac)
        r = res.fun.reshape(out_shape[0]) if out_shape else res.fun
        out = (_shaped(res.x, shape), resnorm,
               _scalar(float(r.reshape(-1)[0])) if r.size == 1
               else _normalise(np.asarray(r)), flag, output)
        if nargout > 5:
            raise MatlabError("Evans's lsqnonlin returns at most five "
                              "outputs [x, resnorm, residual, exitflag, "
                              "output].")
        return out[:nargout] if nargout >= 2 else out[0]

    def _op_jacobian_fn(self, fun, shape):
        def jac(v):
            arg = float(v[0]) if v.size == 1 else v.reshape(shape).copy()
            out = self.rt.call(fun, (arg,), nargout=2)
            if not isinstance(out, tuple) or len(out) < 2:
                raise MatlabError("SpecifyObjectiveGradient is on, so the "
                                  "function must return two outputs.")
            return np.atleast_2d(np.asarray(out[1], float))
        return jac

    @_nargout
    def f_fsolve(self, fun, x0, options=None, *_, nargout=1):
        """
        ``[x, fval, exitflag, output] = fsolve(fun, x0, options)``. A square
        system goes to MINPACK's hybrid Powell dogleg (MATLAB's default is
        a trust-region dogleg too); a non-square one, or a failed dogleg, to
        Levenberg–Marquardt. Solved means ``sum(fval.^2)`` is within
        FunctionTolerance; otherwise exitflag is -2.
        """
        from scipy.optimize import least_squares, root
        self._op_refuse_problem(fun, "fsolve")
        o = self._op_opts(options, "fsolve")
        shape = np.shape(np.asarray(x0, float))
        call = self._op_fn(fun, shape, "fsolve")
        start = np.asarray(x0, float).reshape(-1)
        out_shape = []

        def F(v):
            r = _real_out(call(v), "fsolve")
            if not out_shape:
                out_shape.append(r.shape)
            return r.reshape(-1)

        jac = self._op_jacobian_fn(fun, shape) if o["gradient"] else None
        n, m = start.size, F(start).size
        tolfun = self._op_num(o, "tolfun", 1e-6)
        best = None
        nfev = 0
        if m == n:
            res = root(F, start, method="hybr", jac=jac,
                       options={"xtol": self._op_num(o, "tolx", 1e-12)})
            nfev += int(res.nfev)
            best = res.x
        if best is None or np.sum(F(best) ** 2) > tolfun:
            ls = least_squares(F, start if best is None else best,
                               jac=jac or (lambda v: _central_jac(F, v)),
                               method="lm" if m >= n else "trf",
                               ftol=1e-15, xtol=1e-15, gtol=1e-15)
            nfev += int(ls.nfev)
            if best is None or np.sum(ls.fun ** 2) < np.sum(F(best) ** 2):
                best = ls.x
        fval = F(best)
        resnorm = float(np.sum(fval ** 2))
        if resnorm <= tolfun and np.all(np.isfinite(fval)):
            flag = 1
            self._op_say(o, "\nEquation solved.\n\nfsolve completed because the "
                      "vector of function values is near zero\nas measured "
                      "by the value of the function tolerance, and\nthe "
                      "problem appears regular as measured by the gradient.\n")
        else:
            flag = -2
            self._op_say(o, "\nNo solution found.\n\nfsolve stopped because the "
                      "problem appears regular as measured by the gradient,\n"
                      "but the vector of function values is not near zero as "
                      "measured by the\nvalue of the function tolerance.\n")
        fv = fval.reshape(out_shape[0]) if out_shape else fval
        output = Struct(iterations=nfev, funcCount=nfev,
                        algorithm="trust-region-dogleg",
                        firstorderopt=float(np.max(np.abs(fval))))
        out = (_shaped(best, shape),
               _scalar(float(fv.reshape(-1)[0])) if fv.size == 1
               else _normalise(np.asarray(fv)), flag, output)
        if nargout == 5:
            J = _central_jac(F, best)
            return out + (J,)
        if nargout > 5:
            raise MatlabError("fsolve returns at most five outputs.")
        return out[:nargout] if nargout >= 2 else out[0]

    # ── minimisation ────────────────────────────────────────────

    def _op_objective(self, fun, shape, gradient, who):
        """(f(v), grad(v)) on flat vectors."""
        def call(v, k):
            arg = float(v[0]) if v.size == 1 else v.reshape(shape).copy()
            return self.rt.call(fun, (arg,), nargout=k)

        def f(v):
            return float(_real_out(call(v, 1), who).reshape(-1)[0])

        if gradient:
            def g(v):
                out = call(v, 2)
                if not isinstance(out, tuple) or len(out) < 2:
                    raise MatlabError("SpecifyObjectiveGradient is on, so "
                                      "the objective must return [f, g].")
                return _real_out(out[1], who).reshape(-1)
        else:
            def g(v):
                return _central_grad(f, v)
        return f, g

    @_nargout
    def f_fminunc(self, fun, x0, options=None, *_, nargout=1):
        """``[x, fval, exitflag, output, grad, hessian] = fminunc(...)``."""
        from scipy.optimize import minimize
        self._op_refuse_problem(fun, "fminunc")
        o = self._op_opts(options, "fminunc")
        shape = np.shape(np.asarray(x0, float))
        start = np.asarray(x0, float).reshape(-1)
        f, g = self._op_objective(fun, shape, o["gradient"], "fminunc")
        tol = self._op_num(o, "tolopt", 1e-6)
        g0 = np.max(np.abs(g(start))) if start.size else 0.0
        res = minimize(f, start, jac=g, method="BFGS",
                       options={"gtol": min(tol, 1e-8) * max(1.0, g0),
                                "maxiter": int(self._op_num(o, "maxiter",
                                                         400 * start.size))})
        grad = g(res.x)
        small = np.max(np.abs(grad)) <= tol * max(1.0, g0)
        if res.fun < -1e20:
            flag = -3
            self._op_say(o, "\nProblem appears unbounded.\n\nfminunc stopped "
                      "because the objective function value is less than\n"
                      "the value of the objective function limit.\n")
        elif res.success or small:
            flag = 1
            self._op_say(o, "\nLocal minimum found.\n\nOptimization completed "
                      "because the size of the gradient is less than\nthe "
                      "value of the optimality tolerance.\n")
        elif res.status == 1:
            flag = 0
            self._op_say(o, "\nSolver stopped prematurely.\n\nfminunc stopped "
                      "because it exceeded the iteration limit.\n")
        else:
            flag = 2
            self._op_say(o, "\nLocal minimum possible.\n\nfminunc stopped because "
                      "the size of the current step is less than\nthe value "
                      "of the step size tolerance.\n")
        output = Struct(iterations=int(res.nit), funcCount=int(res.nfev),
                        firstorderopt=float(np.max(np.abs(grad))),
                        algorithm="quasi-newton", message=str(res.message))
        out = (_shaped(res.x, shape), float(res.fun), flag, output,
               _column(grad))
        if nargout >= 6:
            H = _central_jac(g, res.x)
            out += (_normalise((H + H.T) / 2),)
        if nargout > 6:
            raise MatlabError("fminunc returns at most six outputs.")
        return out[:nargout] if nargout >= 2 else out[0]

    @_nargout
    def f_fmincon(self, fun, x0, A=None, b=None, Aeq=None, beq=None,
                  lb=None, ub=None, nonlcon=None, options=None, *_,
                  nargout=1):
        """
        ``[x, fval, exitflag, output] = fmincon(fun, x0, A, b, Aeq, beq, lb,
        ub, nonlcon, options)``: ``A*x <= b``, ``Aeq*x = beq``, bounds and
        ``[c, ceq] = nonlcon(x)`` with ``c <= 0``. Solved by SQP (scipy's
        SLSQP); MATLAB's default is interior-point, which reaches the same
        local minimum on a well-posed problem.
        """
        from scipy.optimize import minimize
        self._op_refuse_problem(fun, "fmincon")
        if nargout > 4:
            raise MatlabError("Evans's fmincon returns at most four outputs "
                              "[x, fval, exitflag, output]; lambda, grad and "
                              "hessian are not supported.")
        o = self._op_opts(options, "fmincon")
        shape = np.shape(np.asarray(x0, float))
        start = np.asarray(x0, float).reshape(-1)
        n = start.size
        f, g = self._op_objective(fun, shape, o["gradient"], "fmincon")
        Ai, bi = _mat(A, n, "A"), _vec(b)
        Ae, be = _mat(Aeq, n, "Aeq"), _vec(beq)
        if (Ai is None) != (bi is None) or (Ai is not None
                                            and Ai.shape[0] != bi.size):
            raise MatlabError("A and b must have the same number of rows.")
        if (Ae is None) != (be is None) or (Ae is not None
                                            and Ae.shape[0] != be.size):
            raise MatlabError("Aeq and beq must have the same number of "
                              "rows.")
        lo, hi = _bounds(lb, ub, n)
        cons = []
        if Ai is not None:
            cons.append({"type": "ineq", "fun": lambda v: bi - Ai @ v,
                         "jac": lambda v: -Ai})
        if Ae is not None:
            cons.append({"type": "eq", "fun": lambda v: Ae @ v - be,
                         "jac": lambda v: Ae})
        cache = {}

        def nonlin(v):
            key = v.tobytes()
            if key not in cache:
                arg = float(v[0]) if v.size == 1 else v.reshape(shape).copy()
                out = self.rt.call(nonlcon, (arg,), nargout=2)
                if not isinstance(out, tuple) or len(out) < 2:
                    raise MatlabError(
                        "The nonlinear constraint function must return two "
                        "outputs, [c, ceq]. Write it as a function with "
                        "outputs [c, ceq]; an anonymous @(x) deal(c, ceq) "
                        "does not pass two outputs in Evans.")
                c = np.zeros(0) if _empty(out[0]) else \
                    _real_out(out[0], "fmincon").reshape(-1)
                ceq = np.zeros(0) if _empty(out[1]) else \
                    _real_out(out[1], "fmincon").reshape(-1)
                cache.clear()
                cache[key] = (c, ceq)
            return cache[key]

        if not _empty(nonlcon):
            c0, ceq0 = nonlin(start)
            if c0.size:
                cons.append({"type": "ineq", "fun": lambda v: -nonlin(v)[0],
                             "jac": lambda v: -_central_jac(
                                 lambda u: nonlin(u)[0], v)})
            if ceq0.size:
                cons.append({"type": "eq", "fun": lambda v: nonlin(v)[1],
                             "jac": lambda v: _central_jac(
                                 lambda u: nonlin(u)[1], v)})
        bnds = [(None if not np.isfinite(lo[i]) else lo[i],
                 None if not np.isfinite(hi[i]) else hi[i]) for i in range(n)]
        start = np.clip(start, lo, hi)
        res = minimize(f, start, jac=g, method="SLSQP", bounds=bnds,
                       constraints=cons,
                       options={"ftol": 1e-12, "maxiter": int(self._op_num(
                           o, "maxiter", 1000))})
        x = res.x
        viol = 0.0
        if Ai is not None:
            viol = max(viol, float(np.max(Ai @ x - bi, initial=0)))
        if Ae is not None:
            viol = max(viol, float(np.max(np.abs(Ae @ x - be), initial=0)))
        viol = max(viol, float(np.max(lo - x, initial=0)),
                   float(np.max(x - hi, initial=0)))
        if not _empty(nonlcon):
            c, ceq = nonlin(x)
            viol = max(viol, float(np.max(c, initial=0)),
                       float(np.max(np.abs(ceq), initial=0)))
        tolcon = self._op_num(o, "tolcon", 1e-6)
        if viol > tolcon:
            flag = -2
            self._op_say(o, "\nNo feasible solution found.\n\nfmincon stopped "
                      "because it could not find a point that satisfies\nthe "
                      "constraints to within the value of the constraint "
                      "tolerance.\n")
        elif res.success:
            flag = 1
            self._op_say(o, "\nLocal minimum found that satisfies the "
                      "constraints.\n\nOptimization completed because the "
                      "objective function is non-decreasing in \nfeasible "
                      "directions, to within the value of the optimality "
                      "tolerance,\nand constraints are satisfied to within "
                      "the value of the constraint tolerance.\n")
        elif res.status == 9:
            flag = 0
            self._op_say(o, "\nSolver stopped prematurely.\n\nfmincon stopped "
                      "because it exceeded the iteration limit.\n")
        else:
            flag = 2
            self._op_say(o, "\nLocal minimum possible. Constraints satisfied."
                      "\n\nfmincon stopped because the size of the current "
                      "step is less than\nthe value of the step size "
                      "tolerance and constraints are \nsatisfied to within "
                      "the value of the constraint tolerance.\n")
        output = Struct(iterations=int(res.nit), funcCount=int(res.nfev),
                        constrviolation=viol, algorithm="sqp",
                        message=str(res.message))
        out = (_shaped(x, shape), float(f(x)), flag, output)
        return out[:nargout] if nargout >= 2 else out[0]

    # ── linear, integer and quadratic programming ───────────────

    def _op_lp_parts(self, f, A, b, Aeq, beq, lb, ub, who):
        c = _vec(f)
        if c is None:
            raise MatlabError(f"{who}: f must not be empty.")
        n = c.size
        Ai, bi = _mat(A, n, "A"), _vec(b)
        Ae, be = _mat(Aeq, n, "Aeq"), _vec(beq)
        if (Ai is None) != (bi is None) or (Ai is not None
                                            and Ai.shape[0] != bi.size):
            raise MatlabError("The number of rows in A must be the same as "
                              "the number of elements of b.")
        if (Ae is None) != (be is None) or (Ae is not None
                                            and Ae.shape[0] != be.size):
            raise MatlabError("The number of rows in Aeq must be the same as "
                              "the number of elements of beq.")
        lo, hi = _bounds(lb, ub, n)
        return c, Ai, bi, Ae, be, lo, hi

    @_nargout
    def f_linprog(self, f, A=None, b=None, Aeq=None, beq=None, lb=None,
                  ub=None, options=None, *_, nargout=1):
        """``[x, fval, exitflag, output, lambda] = linprog(...)``, by HiGHS."""
        from scipy.optimize import linprog
        self._op_refuse_problem(f, "linprog")
        o = self._op_opts(options, "linprog")
        c, Ai, bi, Ae, be, lo, hi = self._op_lp_parts(f, A, b, Aeq, beq, lb, ub,
                                                   "linprog")
        algo = o["algorithm"]
        method = "highs"
        if isinstance(algo, str):
            method = {"dual-simplex": "highs-ds", "dual-simplex-highs":
                      "highs-ds", "interior-point": "highs-ipm",
                      "interior-point-legacy": "highs-ipm"}.get(
                          algo.lower(), "highs")
        res = linprog(c, A_ub=Ai, b_ub=bi, A_eq=Ae, b_eq=be,
                      bounds=list(zip(lo, hi, strict=True)), method=method)
        flag = {0: 1, 1: 0, 2: -2, 3: -3, 4: -4}.get(res.status, -4)
        text = {1: "\nOptimal solution found.\n",
                0: "\nSolver stopped prematurely.\n\nlinprog stopped because "
                   "it exceeded the iteration limit.\n",
                -2: "\nNo feasible solution found.\n\nLinprog stopped because "
                    "no point satisfies the constraints.\n",
                -3: "\nProblem is unbounded.\n\nLinprog stopped because the "
                    "objective function is unbounded below.\n",
                -4: "\nSolver stopped: numerical difficulties.\n"}[flag]
        self._op_say(o, text)
        empty = np.zeros((0, 0))
        if flag in (1, 0) and res.x is not None:
            x, fval = res.x.reshape(-1, 1), float(res.fun)
        else:
            x, fval = empty, empty
        output = Struct(iterations=int(getattr(res, "nit", 0)),
                        algorithm="dual-simplex" if method != "highs-ipm"
                        else "interior-point", message=str(res.message))
        out = (x if x.size != 1 else _scalar(float(x[0, 0])), fval, flag,
               output)
        if nargout >= 5:
            n = c.size

            def marg(part, size):
                m = getattr(res, part, None)
                return np.zeros(size) if m is None else np.asarray(
                    m.marginals, float)
            lam = Struct(
                ineqlin=-marg("ineqlin", 0 if Ai is None else Ai.shape[0])
                .reshape(-1, 1),
                eqlin=-marg("eqlin", 0 if Ae is None else Ae.shape[0])
                .reshape(-1, 1),
                lower=marg("lower", n).reshape(-1, 1),
                upper=-marg("upper", n).reshape(-1, 1))
            out += (lam,)
        if nargout > 5:
            raise MatlabError("linprog returns at most five outputs.")
        return out[:nargout] if nargout >= 2 else out[0]

    @_nargout
    def f_intlinprog(self, f, intcon, A=None, b=None, Aeq=None, beq=None,
                     lb=None, ub=None, x0=None, options=None, *_, nargout=1):
        """``[x, fval, exitflag, output] = intlinprog(f, intcon, ...)``."""
        from scipy.optimize import Bounds, LinearConstraint, milp
        self._op_refuse_problem(f, "intlinprog")
        if isinstance(x0, Mapping) and options is None:
            x0, options = None, x0
        o = self._op_opts(options, "intlinprog")
        c, Ai, bi, Ae, be, lo, hi = self._op_lp_parts(f, A, b, Aeq, beq, lb, ub,
                                                   "intlinprog")
        n = c.size
        integrality = np.zeros(n)
        ic = _vec(intcon)
        if ic is not None:
            if np.any(ic < 1) or np.any(ic > n) or np.any(ic != np.round(ic)):
                raise MatlabError("intcon must contain integers between 1 "
                                  "and the number of variables.")
            integrality[ic.astype(int) - 1] = 1
        cons = []
        if Ai is not None:
            cons.append(LinearConstraint(Ai, -np.inf, bi))
        if Ae is not None:
            cons.append(LinearConstraint(Ae, be, be))
        res = milp(c, integrality=integrality, bounds=Bounds(lo, hi),
                   constraints=cons, options={
                       "mip_rel_gap": self._op_num(o, "relgap", 1e-6),
                       "disp": False})
        if res.status == 4:
            raise MatlabError(f"intlinprog failed: {res.message}")
        feasible = res.x is not None
        flag = {0: 1, 1: 2 if feasible else 0, 2: -2, 3: -3}[res.status]
        text = {1: "\nOptimal solution found.\n\nIntlinprog stopped because "
                   "the objective value is within a gap tolerance of the "
                   "optimal value.\nThe intcon variables are integer within "
                   "tolerance.\n",
                2: "\nIntlinprog stopped with a feasible point that is not "
                   "proven optimal (a limit was reached).\n",
                0: "\nIntlinprog stopped: a limit was reached before any "
                   "integer feasible point was found.\n",
                -2: "\nNo feasible solution found.\n\nIntlinprog stopped "
                    "because no point satisfies the constraints.\n",
                -3: "\nProblem is unbounded.\n\nIntlinprog stopped because "
                    "the root LP problem is unbounded.\n"}[flag]
        self._op_say(o, text)
        empty = np.zeros((0, 0))
        if feasible:
            x = res.x.copy()
            mask = integrality == 1
            x[mask] = np.round(x[mask])
            fval = float(c @ x)
            x = x.reshape(-1, 1) if n > 1 else _scalar(float(x[0]))
        else:
            x, fval = empty, empty
        output = Struct(relativegap=float(getattr(res, "mip_gap", 0) or 0),
                        numnodes=int(getattr(res, "mip_node_count", 0) or 0),
                        message=str(res.message))
        out = (x, fval, flag, output)
        if nargout > 4:
            raise MatlabError("intlinprog returns at most four outputs.")
        return out[:nargout] if nargout >= 2 else out[0]

    @_nargout
    def f_quadprog(self, H, f=None, A=None, b=None, Aeq=None, beq=None,
                   lb=None, ub=None, x0=None, options=None, *_, nargout=1):
        """
        ``[x, fval, exitflag, output, lambda] = quadprog(H, f, A, b, Aeq,
        beq, lb, ub)``: minimise ``0.5*x'*H*x + f'*x``. Convex problems only,
        as MATLAB's default interior-point-convex. The answer is the exact
        KKT point of the active set an SQP run identifies.
        """
        from scipy.optimize import linprog, minimize
        self._op_refuse_problem(H, "quadprog")
        if isinstance(x0, Mapping) and options is None:
            x0, options = None, x0
        o = self._op_opts(options, "quadprog")
        Hm = np.atleast_2d(np.asarray(H, float))
        n = Hm.shape[0]
        if Hm.shape != (n, n):
            raise MatlabError("H must be a square matrix.")
        Hm = (Hm + Hm.T) / 2
        fv = _vec(f, n, "f")
        fv = np.zeros(n) if fv is None else fv
        _, Ai, bi, Ae, be, lo, hi = self._op_lp_parts(
            np.ones(n), A, b, Aeq, beq, lb, ub, "quadprog")
        empty = np.zeros((0, 0))

        def finish(x, flag, text, mult=None):
            self._op_say(o, text)
            if x is None:
                out = (empty, empty, flag, Struct(algorithm=
                       "interior-point-convex", message=text.strip().splitlines()[0]))
                return (out + (Struct(),))[:nargout] if nargout >= 2 \
                    else empty
            fval = float(0.5 * x @ Hm @ x + fv @ x)
            output = Struct(algorithm="interior-point-convex",
                            constrviolation=viol(x), message=text.strip().splitlines()[0])
            out = (_column(x), fval, flag, output)
            if nargout >= 5:
                out += (mult,)
            if nargout > 5:
                raise MatlabError("quadprog returns at most five outputs.")
            return out[:nargout] if nargout >= 2 else out[0]

        def viol(x):
            v = 0.0
            if Ai is not None:
                v = max(v, float(np.max(Ai @ x - bi, initial=0)))
            if Ae is not None:
                v = max(v, float(np.max(np.abs(Ae @ x - be), initial=0)))
            return max(v, float(np.max(lo - x, initial=0)),
                       float(np.max(x - hi, initial=0)))

        eigs = np.linalg.eigvalsh(Hm) if n else np.zeros(0)
        scale = max(1.0, float(np.max(np.abs(eigs), initial=0)))
        if eigs.size and eigs[0] < -1e-10 * scale:
            return finish(None, -6, "\nNon-convex problem detected.\n\n"
                          "quadprog stopped because it detected a non-convex "
                          "problem (H is not positive semidefinite).\n")
        bnds = list(zip(lo, hi, strict=True))
        # Feasibility first, by an LP with no objective.
        constrained = Ai is not None or Ae is not None or np.any(
            np.isfinite(lo)) or np.any(np.isfinite(hi))
        start = np.zeros(n)
        if constrained:
            lp = linprog(np.zeros(n), A_ub=Ai, b_ub=bi, A_eq=Ae, b_eq=be,
                         bounds=bnds, method="highs")
            if lp.status == 2:
                return finish(None, -2, "\nNo feasible solution found.\n\n"
                              "quadprog stopped because no point satisfies "
                              "the constraints.\n")
            start = lp.x
        # Unbounded: a recession direction d with H d = 0 and f'd < 0.
        if eigs.size and eigs[0] <= 1e-10 * scale:
            Aub = [] if Ai is None else [Ai]
            dlo = np.where(np.isfinite(lo), 0, -1.0)
            dhi = np.where(np.isfinite(hi), 0, 1.0)
            eq = [Hm] + ([] if Ae is None else [Ae])
            lp = linprog(fv, A_ub=np.vstack(Aub) if Aub else None,
                         b_ub=np.zeros(Ai.shape[0]) if Ai is not None
                         else None, A_eq=np.vstack(eq),
                         b_eq=np.zeros(sum(e.shape[0] for e in eq)),
                         bounds=list(zip(dlo, dhi, strict=True)),
                         method="highs")
            if lp.status == 0 and lp.fun < -1e-9 * max(1.0, np.max(
                    np.abs(fv))):
                return finish(None, -3, "\nProblem is unbounded.\n\nquadprog "
                              "stopped because the objective function is "
                              "unbounded below.\n")

        def kkt(active_A, active_lo, active_hi):
            rows, rhs, kinds = [], [], []
            if Ai is not None:
                for i in np.nonzero(active_A)[0]:
                    rows.append(Ai[i]); rhs.append(bi[i]); kinds.append(("A", i))
            if Ae is not None:
                for i in range(Ae.shape[0]):
                    rows.append(Ae[i]); rhs.append(be[i]); kinds.append(("E", i))
            for i in np.nonzero(active_lo)[0]:
                e = np.zeros(n); e[i] = -1
                rows.append(e); rhs.append(-lo[i]); kinds.append(("L", i))
            for i in np.nonzero(active_hi)[0]:
                e = np.zeros(n); e[i] = 1
                rows.append(e); rhs.append(hi[i]); kinds.append(("U", i))
            G = np.array(rows).reshape(len(rows), n)
            k = G.shape[0]
            K = np.block([[Hm, G.T], [G, np.zeros((k, k))]])
            sol = np.linalg.lstsq(K, np.concatenate([-fv, rhs]), rcond=None)[0]
            return sol[:n], sol[n:], kinds

        def multipliers(mu, kinds):
            lam = Struct(ineqlin=np.zeros((0 if Ai is None else Ai.shape[0],
                                           1)),
                         eqlin=np.zeros((0 if Ae is None else Ae.shape[0], 1)),
                         lower=np.zeros((n, 1)), upper=np.zeros((n, 1)))
            key = {"A": "ineqlin", "E": "eqlin", "L": "lower", "U": "upper"}
            for m, (kind, i) in zip(mu, kinds, strict=True):
                lam[key[kind]][i, 0] = m
            return lam

        if not constrained or (Ai is None and not np.any(np.isfinite(lo))
                               and not np.any(np.isfinite(hi))):
            x, mu, kinds = kkt(np.zeros(0, bool), np.zeros(n, bool),
                               np.zeros(n, bool))
        else:
            cons = []
            if Ai is not None:
                cons.append({"type": "ineq", "fun": lambda v: bi - Ai @ v,
                             "jac": lambda v: -Ai})
            if Ae is not None:
                cons.append({"type": "eq", "fun": lambda v: Ae @ v - be,
                             "jac": lambda v: Ae})
            res = minimize(lambda v: 0.5 * v @ Hm @ v + fv @ v, start,
                           jac=lambda v: Hm @ v + fv, method="SLSQP",
                           bounds=[(None if not np.isfinite(a) else a,
                                    None if not np.isfinite(c) else c)
                                   for a, c in bnds],
                           constraints=cons,
                           options={"ftol": 1e-15, "maxiter": 2000})
            x = res.x
            tol = 1e-6
            act_A = (np.abs(Ai @ x - bi) <= tol * (1 + np.abs(bi))) \
                if Ai is not None else np.zeros(0, bool)
            act_lo = np.abs(x - lo) <= tol * (1 + np.abs(np.where(
                np.isfinite(lo), lo, 0)))
            act_hi = np.abs(x - hi) <= tol * (1 + np.abs(np.where(
                np.isfinite(hi), hi, 0)))
            xp, mu, kinds = kkt(act_A, act_lo, act_hi)
            signs_ok = all(m >= -1e-8 for m, (k, _) in zip(mu, kinds,
                                                           strict=True)
                           if k != "E")
            if viol(xp) <= 1e-9 * (1 + np.max(np.abs(xp))) and signs_ok:
                x = xp
            else:
                mu, kinds = [], []
        return finish(x, 1, "\nMinimum found that satisfies the constraints."
                      "\n\nOptimization completed because the objective "
                      "function is non-decreasing in \nfeasible directions, "
                      "to within the value of the optimality tolerance,\nand "
                      "constraints are satisfied to within the value of the "
                      "constraint tolerance.\n", multipliers(mu, kinds))

    # ── quadrature ──────────────────────────────────────────────

    def _op_integrand(self, fun, array_valued, who):
        """g(x) for an array of nodes, last axis the nodes."""
        def g(x):
            if array_valued:
                vals = [np.asarray(self.rt.call(fun, (float(xi),),
                                                nargout=1)) for xi in x]
                return np.moveaxis(np.array(vals), 0, -1)
            out = np.asarray(self.rt.call(fun, (x.copy(),), nargout=1))
            if out.size != x.size:
                raise MatlabError(
                    "Output of the function must be the same size as the "
                    "input. If FUN is an array-valued integrand, set the "
                    "'ArrayValued' option to true.")
            return out.reshape(-1)
        return g

    def _op_quad(self, fun, a, b, opts, who, default_reltol=1e-6):
        array_valued = _truthy(opts.get("ArrayValued", False))
        abstol = float(_scalar(opts.get("AbsTol", 1e-10)))
        reltol = float(_scalar(opts.get("RelTol", default_reltol)))
        maxint = int(_scalar(opts.get("MaxIntervalCount", 650)))
        for v in (a, b):
            if _numel(v) != 1 or np.iscomplexobj(np.asarray(v)):
                raise MatlabError(f"{who}: the limits must be real scalars "
                                  "(Evans does not integrate along complex "
                                  "contours).")
        a, b = float(np.real(_scalar(a))), float(np.real(_scalar(b)))
        g = self._op_integrand(fun, array_valued, who)
        points = [a, b]
        way = opts.get("Waypoints")
        if not _empty(way):
            w = np.asarray(way)
            if np.iscomplexobj(w):
                raise MatlabError(f"{who}: complex waypoints (contour "
                                  "integrals) are not supported.")
            w = np.sort(w.astype(float).reshape(-1))
            inner = [p for p in w if min(a, b) < p < max(a, b)]
            points = [a] + (inner if a < b else inner[::-1]) + [b]
        total, err = 0.0, 0.0
        for lo, hi in zip(points[:-1], points[1:], strict=True):
            if lo == hi:
                continue

            def weighted(t, lo=lo, hi=hi):
                x, w = _path(lo, hi, t)
                return g(x) * w
            q, e = _gk_adapt(weighted, abstol, reltol, maxint, who)
            total, err = total + q, err + e
        if np.ndim(total) == 0:
            total = complex(total) if np.iscomplexobj(total) else \
                float(total)
            if isinstance(total, complex) and total.imag == 0:
                total = total.real
            return total, float(np.max(err))
        return _normalise(np.asarray(total)), float(np.max(err))

    def f_integral(self, fun, a, b, *options):
        """``integral(fun, a, b, 'AbsTol', .., 'RelTol', .., 'ArrayValued',
        tf, 'Waypoints', w)``."""
        opts = _name_values(options, ("AbsTol", "RelTol", "ArrayValued",
                                      "Waypoints"), "integral")
        return self._op_quad(fun, a, b, opts, "integral")[0]

    @_nargout
    def f_quadgk(self, fun, a, b, *options, nargout=1):
        """``[q, errbnd] = quadgk(fun, a, b, Name, Value)``."""
        opts = _name_values(options, ("AbsTol", "RelTol", "Waypoints",
                                      "MaxIntervalCount"), "quadgk")
        q, e = self._op_quad(fun, a, b, opts, "quadgk")
        return (q, e) if nargout >= 2 else q

    def f_integral2(self, fun, xmin, xmax, ymin, ymax, *options):
        """
        ``integral2(fun, xmin, xmax, ymin, ymax)``, iterated: the inner
        integral over y for a whole batch of x nodes at once. ``ymin`` and
        ``ymax`` may be handles of x.
        """
        opts = _name_values(options, ("AbsTol", "RelTol", "Method"),
                            "integral2")
        method = str(opts.get("Method", "auto")).lower()
        if method not in ("auto", "tiled", "iterated"):
            raise MatlabError("Method must be 'auto', 'tiled' or 'iterated'.")
        abstol = float(_scalar(opts.get("AbsTol", 1e-10)))
        reltol = float(_scalar(opts.get("RelTol", 1e-6)))
        for v in (xmin, xmax):
            if _numel(v) != 1:
                raise MatlabError("xmin and xmax must be scalars.")
        x0, x1 = float(_scalar(xmin)), float(_scalar(xmax))

        def limit(lim, xs):
            if _is_function(lim) or callable(lim) and not isinstance(
                    lim, (np.ndarray, str)):
                out = np.asarray(self.rt.call(lim, (xs.copy(),), nargout=1),
                                 float).reshape(-1)
                return np.broadcast_to(out, xs.shape) if out.size == 1 \
                    else out
            return np.full(xs.shape, float(_scalar(lim)))

        def inner(xs):
            c = limit(ymin, xs)[:, None]
            d = limit(ymax, xs)[:, None]

            def weighted(t):
                y, w = _path(c, d, t[None, :])
                X = np.broadcast_to(xs[:, None], y.shape).copy()
                out = np.asarray(self.rt.call(fun, (X, y.copy()),
                                              nargout=1), float)
                if out.size != y.size:
                    raise MatlabError("Integrand output size does not match "
                                      "the input size.")
                return out.reshape(y.shape) * w
            return _gk_adapt(weighted, abstol, reltol, 650, "integral2")[0]

        def outer(t):
            xs, w = _path(x0, x1, t)
            return inner(xs) * w
        q = _gk_adapt(outer, abstol, reltol, 650, "integral2")[0]
        return float(q)

    # ── polynomials and splines ─────────────────────────────────

    @staticmethod
    def _op_strip(p):
        p = np.asarray(p, float).reshape(-1)
        nz = np.nonzero(p)[0]
        return p[nz[0]:] if nz.size else np.zeros(1)

    @staticmethod
    def _op_deriv(p):
        p = np.asarray(p, float).reshape(-1)
        if p.size <= 1:
            return np.zeros(1)
        return p[:-1] * np.arange(p.size - 1, 0, -1)

    @staticmethod
    def _op_poly_out(p):
        return _scalar(float(p[0])) if p.size == 1 else p

    @_nargout
    def f_polyder(self, u, v=None, nargout=1):
        """
        ``polyder(p)``, ``polyder(a, b)`` (of the product) and
        ``[q, d] = polyder(b, a)`` (of the quotient b/a).
        """
        if v is None:
            if nargout >= 2:
                raise MatlabError("polyder with two outputs needs two "
                                  "polynomials, [q, d] = polyder(b, a).")
            return self._op_poly_out(self._op_strip(self._op_deriv(u)))
        a = np.asarray(u, float).reshape(-1)
        b = np.asarray(v, float).reshape(-1)
        if nargout < 2:
            return self._op_poly_out(self._op_strip(self._op_deriv(np.convolve(a, b))))
        # d/dx (a/b) = (a' b - a b') / b²
        t1 = np.convolve(self._op_deriv(a), b)
        t2 = np.convolve(a, self._op_deriv(b))
        size = max(t1.size, t2.size)
        q = np.pad(t1, (size - t1.size, 0)) - np.pad(t2, (size - t2.size, 0))
        d = np.convolve(b, b)
        return self._op_poly_out(self._op_strip(q)), self._op_poly_out(self._op_strip(d))

    def f_polyint(self, p, k=0):
        p = np.asarray(p, float).reshape(-1)
        out = np.concatenate([p / np.arange(p.size, 0, -1),
                              [float(_scalar(k))]])
        return self._op_poly_out(out)

    @staticmethod
    def _op_xy(x, y, who):
        xv = np.asarray(x, float).reshape(-1)
        Y = np.asarray(y, float)
        if Y.ndim < 2 or 1 in Y.shape:
            Y = Y.reshape(1, -1)
        if xv.size < 2:
            raise MatlabError(f"{who} needs at least two sample points.")
        if np.any(np.diff(np.sort(xv)) == 0):
            raise MatlabError("The data sites should be distinct.")
        return xv, Y

    def _op_pp_struct(self, pp, d):
        """MATLAB's pp form from a scipy PPoly over axis 1 of a d×n array."""
        c = np.asarray(pp.c)                       # (4, pieces, d)
        k, pieces = c.shape[0], c.shape[1]
        coefs = c.reshape(k, pieces, d).transpose(1, 2, 0).reshape(
            pieces * d, k)
        return Struct(form="pp", breaks=np.asarray(pp.x, float),
                      coefs=_normalise(coefs), pieces=pieces, order=k, dim=d)

    def _op_evaluate(self, poly, xq, d):
        q = np.asarray(xq, float)
        vals = np.asarray(poly(q.reshape(-1)))     # (m, d)
        if d == 1:
            out = vals.reshape(q.shape)
            return _scalar(float(out)) if out.ndim == 0 else out
        return _normalise(vals.T)

    def f_spline(self, x, y, xq=None):
        """
        Not-a-knot cubic spline, MATLAB's: a straight line through two
        points, a parabola through three. With two more values than sites,
        the first and last are the end slopes (a clamped spline).
        """
        from scipy.interpolate import CubicSpline
        xv, Y = self._op_xy(x, y, "spline")
        n = xv.size
        if Y.shape[1] == n + 2:
            bc = ((1, Y[:, 0]), (1, Y[:, -1])) if Y.shape[0] > 1 else \
                ((1, float(Y[0, 0])), (1, float(Y[0, -1])))
            Y = Y[:, 1:-1]
        elif Y.shape[1] == n:
            bc = "not-a-knot"
        else:
            raise MatlabError("The number of sites, x, must match the number "
                              "of values, y (or be two fewer, for end "
                              "slopes).")
        order = np.argsort(xv)
        xv, Y = xv[order], Y[:, order]
        d = Y.shape[0]
        poly = CubicSpline(xv, Y.T if d > 1 else Y[0], bc_type=bc, axis=0)
        if xq is None:
            return self._op_pp_struct(poly, d)
        return self._op_evaluate(poly, xq, d)

    def f_pchip(self, x, y, xq=None):
        """Shape-preserving piecewise cubic (Fritsch–Carlson, as MATLAB)."""
        from scipy.interpolate import PchipInterpolator
        xv, Y = self._op_xy(x, y, "pchip")
        if Y.shape[1] != xv.size:
            raise MatlabError("The number of sites, x, must match the number "
                              "of values, y.")
        order = np.argsort(xv)
        xv, Y = xv[order], Y[:, order]
        d = Y.shape[0]
        poly = PchipInterpolator(xv, Y.T if d > 1 else Y[0], axis=0)
        if xq is None:
            return self._op_pp_struct(poly, d)
        return self._op_evaluate(poly, xq, d)

    def f_ppval(self, pp, xq):
        """Evaluate a pp structure (from spline or pchip) at ``xq``."""
        if not isinstance(pp, Mapping) or pp.get("form") != "pp":
            raise MatlabError("ppval needs a piecewise polynomial structure, "
                              "as spline(x, y) returns.")
        breaks = np.asarray(pp["breaks"], float).reshape(-1)
        coefs = np.atleast_2d(np.asarray(pp["coefs"], float))
        d, k = int(pp["dim"]), int(pp["order"])
        pieces = breaks.size - 1
        q = np.asarray(xq, float)
        flat = q.reshape(-1)
        idx = np.clip(np.searchsorted(breaks, flat, side="right") - 1, 0,
                      pieces - 1)
        s = flat - breaks[idx]
        out = np.zeros((d, flat.size))
        for j in range(d):
            C = coefs[idx * d + j]                 # (m, k)
            acc = np.zeros(flat.size)
            for m in range(k):
                acc = acc * s + C[:, m]
            out[j] = acc
        out[:, np.isnan(flat)] = np.nan
        if d == 1:
            res = out[0].reshape(q.shape)
            return _scalar(float(res)) if res.ndim == 0 else res
        return _normalise(out)

    # ── 2-D interpolation ───────────────────────────────────────

    @staticmethod
    def _op_query_grid(xq, yq):
        """MATLAB's rule: vectors of different orientation form a grid."""
        Xq, Yq = np.asarray(xq, float), np.asarray(yq, float)
        rx, cx = _shape(xq)
        ry, cy = _shape(yq)
        if rx == 1 and cy == 1 and cx > 1 and ry > 1:
            return np.meshgrid(Xq.reshape(-1), Yq.reshape(-1))
        if cx == 1 and ry == 1 and rx > 1 and cy > 1:
            return np.meshgrid(Xq.reshape(-1), Yq.reshape(-1))
        if Xq.shape != Yq.shape:
            Xq, Yq = np.broadcast_arrays(Xq, Yq)
        return Xq, Yq

    @staticmethod
    def _op_shape_out(out):
        out = np.asarray(out, float)
        return _scalar(float(out)) if out.size == 1 else _normalise(out)

    def f_interp2(self, *args):
        """
        ``interp2(X, Y, V, Xq, Yq[, method[, extrapval]])`` or
        ``interp2(V, Xq, Yq[, method])``. 'linear' (default), 'nearest',
        'spline' (MATLAB's not-a-knot spline along each dimension). NaN
        outside the grid unless ``extrapval`` is given.
        """
        from scipy.interpolate import CubicSpline, RegularGridInterpolator
        k = next((i for i, a in enumerate(args) if isinstance(a, str)),
                 len(args))
        data, rest = args[:k], args[k:]
        method = "linear"
        fill = math.nan
        if rest:
            method = str(rest[0]).lower().lstrip("*")
            if len(rest) > 1:
                fill = float(_scalar(rest[1]))
        if len(data) == 3:
            V = np.atleast_2d(np.asarray(data[0], float))
            x = np.arange(1.0, V.shape[1] + 1)
            y = np.arange(1.0, V.shape[0] + 1)
            xq, yq = data[1], data[2]
        elif len(data) == 5:
            X, Y = np.asarray(data[0], float), np.asarray(data[1], float)
            V = np.atleast_2d(np.asarray(data[2], float))
            xq, yq = data[3], data[4]
            if X.ndim == 2 and min(X.shape) > 1:
                x, y = X[0, :], Y[:, 0]
                if not (np.allclose(X, x[None, :]) and
                        np.allclose(Y, y[:, None])):
                    raise MatlabError("Interpolation requires a grid in "
                                      "meshgrid format.")
            else:
                x, y = X.reshape(-1), Y.reshape(-1)
        else:
            raise MatlabError("Evans's interp2 takes interp2(X, Y, V, Xq, Yq) "
                              "or interp2(V, Xq, Yq) (not the refinement "
                              "form interp2(V, k)).")
        if V.shape != (y.size, x.size):
            raise MatlabError("The lengths of X and Y must match the size of "
                              "V: columns of V for X, rows for Y.")
        ox, oy = np.argsort(x), np.argsort(y)
        x, y, V = x[ox], y[oy], V[np.ix_(oy, ox)]
        if np.any(np.diff(x) == 0) or np.any(np.diff(y) == 0):
            raise MatlabError("The grid vectors must be strictly monotonic.")
        Xq, Yq = self._op_query_grid(xq, yq)
        fx, fy = Xq.reshape(-1), Yq.reshape(-1)
        if method in ("linear", "nearest"):
            f = RegularGridInterpolator((y, x), V, method=method,
                                        bounds_error=False, fill_value=fill)
            out = f(np.column_stack([fy, fx]))
        elif method == "spline":
            Wx = CubicSpline(x, np.eye(x.size), axis=0)(fx)   # (q, nx)
            Wy = CubicSpline(y, np.eye(y.size), axis=0)(fy)   # (q, ny)
            out = np.einsum("qi,ij,qj->q", Wy, V, Wx)
        elif method in ("cubic", "makima"):
            raise MatlabError(f"Evans's interp2 does not support '{method}'; "
                              "use 'spline', 'linear' or 'nearest'.")
        else:
            raise MatlabError(f"Invalid interpolation method '{method}'.")
        outside = (fx < x[0]) | (fx > x[-1]) | (fy < y[0]) | (fy > y[-1])
        out = np.asarray(out, float)
        out[outside] = fill
        out[np.isnan(fx) | np.isnan(fy)] = np.nan
        return self._op_shape_out(out.reshape(Xq.shape))

    def f_griddata(self, x, y, v, xq, yq, method="linear", *rest):
        """
        Scattered-data interpolation on a Delaunay triangulation: 'linear'
        (default) or 'nearest'; NaN outside the convex hull, as MATLAB.
        """
        from scipy.interpolate import griddata
        from scipy.spatial import Delaunay
        if rest:
            raise MatlabError("Evans's griddata takes no options after the "
                              "method.")
        method = str(method).lower()
        if method not in ("linear", "nearest"):
            raise MatlabError(f"Evans's griddata supports 'linear' and "
                              f"'nearest'; '{method}' is not supported.")
        pts = np.column_stack([np.asarray(x, float).reshape(-1),
                               np.asarray(y, float).reshape(-1)])
        vals = np.asarray(v, float).reshape(-1)
        if vals.size != pts.shape[0]:
            raise MatlabError("The sizes of x, y and v must agree.")
        uniq, inv = np.unique(pts, axis=0, return_inverse=True)
        inv = inv.reshape(-1)
        if uniq.shape[0] < pts.shape[0]:
            print("Warning: Duplicate data points have been detected and "
                  "removed - corresponding values have been averaged.")
            vals = np.bincount(inv, vals) / np.bincount(inv)
            pts = uniq
        Xq, Yq = self._op_query_grid(xq, yq)
        q = np.column_stack([Xq.reshape(-1), Yq.reshape(-1)])
        out = griddata(pts, vals, q, method=method)
        if method == "nearest":
            out = np.asarray(out, float)
            out[Delaunay(pts).find_simplex(q) < 0] = np.nan
        return self._op_shape_out(np.asarray(out).reshape(Xq.shape))

    # ── curve fitting ───────────────────────────────────────────

    @_nargout
    def f_fit(self, x, y, fittype, *options, nargout=1):
        """
        ``[f, gof, output] = fit(x, y, 'exp1', Name, Value)`` for the library
        models. Polynomials are linear least squares, exactly; the others
        start from a data-driven guess (or 'StartPoint') and go to the
        least-squares optimum by Levenberg–Marquardt (or trust-region
        reflective with 'Lower'/'Upper'). Confidence bounds come from the
        Jacobian at the optimum and Student's t, as MATLAB's.
        """
        from scipy import stats
        from scipy.optimize import least_squares, lsq_linear
        if not isinstance(fittype, str):
            raise MatlabError("Evans's fit takes the model as text, such as "
                              "'poly2' or 'exp1'.")
        kind, key, names, formula, fn, degree = _model(fittype)
        opts = _name_values(options, ("StartPoint", "Lower", "Upper",
                                      "Weights", "Exclude", "Robust",
                                      "Normalize"), "fit")
        if str(opts.get("Robust", "off")).lower() not in ("off",):
            raise MatlabError("Evans's fit does not support robust fitting.")
        if str(opts.get("Normalize", "off")).lower() not in ("off",):
            raise MatlabError("Evans's fit does not support "
                              "'Normalize', 'on'.")
        xv = np.asarray(x, float)
        yv = np.asarray(y, float)
        if xv.ndim == 2 and min(xv.shape) > 1:
            raise MatlabError("Evans's fit takes curve data only: x must be "
                              "a vector (surface fits are not supported).")
        xv, yv = xv.reshape(-1), yv.reshape(-1)
        if xv.size != yv.size:
            raise MatlabError("X and Y must have the same number of rows.")
        if not (np.all(np.isfinite(xv)) and np.all(np.isfinite(yv))):
            raise MatlabError("X and Y must not contain NaN or Inf values.")
        w = _vec(opts.get("Weights"))
        w = np.ones(xv.size) if w is None else w
        if w.size != xv.size:
            raise MatlabError("Weights must have one value per data point.")
        keep = np.ones(xv.size, bool)
        ex = opts.get("Exclude")
        if not _empty(ex):
            e = np.asarray(ex)
            if e.dtype == bool:
                keep &= ~e.reshape(-1)
            else:
                keep[e.astype(int).reshape(-1) - 1] = False
        xv, yv, w = xv[keep], yv[keep], w[keep]
        p = len(names)
        if key in ("power1", "power2") and np.any(xv <= 0):
            raise MatlabError("Cannot fit Power functions to data where X "
                              "has nonpositive values.")
        if xv.size < p:
            raise MatlabError("Insufficient data: there must be at least as "
                              "many data points as coefficients.")
        sw = np.sqrt(w)
        lo = _vec(opts.get("Lower"), p, "Lower")
        hi = _vec(opts.get("Upper"), p, "Upper")
        lo = np.full(p, -np.inf) if lo is None else lo
        hi = np.full(p, np.inf) if hi is None else hi
        bounded = np.any(np.isfinite(lo)) or np.any(np.isfinite(hi))
        iterations, exitflag = 0, 1
        if kind == "Linear":
            B = np.vander(xv, degree + 1)
            if bounded:
                coef = lsq_linear(B * sw[:, None], yv * sw, bounds=(lo, hi),
                                  tol=1e-14).x
            else:
                coef = _linear_ls(B * sw[:, None], yv * sw)
            J = B
            algorithm = "QR factorization and solve"
        else:
            start = _vec(opts.get("StartPoint"), p, "StartPoint")
            if start is None:
                start = np.clip(_start(key, xv, yv), lo, hi)

            def resid(c):
                return (fn(c, xv) - yv) * sw
            res = least_squares(resid, start, jac=lambda c: _central_jac(resid, c),
                                method="trf" if bounded else "lm",
                                bounds=(lo, hi), ftol=1e-15, xtol=1e-15,
                                gtol=1e-15, max_nfev=2000 * p)
            coef = res.x
            if key == "sin1" and coef[0] < 0:
                coef = np.array([-coef[0], coef[1], coef[2] + math.pi])
            if key == "gauss1":
                coef[2] = abs(coef[2])      # the model is even in c1
            J = _central_jac(lambda c: fn(c, xv), coef)
            iterations = int(res.nfev)
            exitflag = {1: 1, 2: 3, 3: 2, 4: 3, 0: 0}.get(res.status, 1)
            algorithm = "Trust-Region" if bounded else "Levenberg-Marquardt"
        r = yv - fn(coef, xv)
        sse = float(np.sum(w * r ** 2))
        ybar = np.sum(w * yv) / np.sum(w)
        sst = float(np.sum(w * (yv - ybar) ** 2))
        n = xv.size
        dfe = n - p
        rsq = 1 - sse / sst if sst > 0 else math.nan
        gof = Struct(sse=sse, rsquare=rsq, dfe=dfe,
                     adjrsquare=1 - (1 - rsq) * (n - 1) / dfe if dfe > 0
                     else math.nan,
                     rmse=math.sqrt(sse / dfe) if dfe > 0 else math.nan)
        bounds = None
        if dfe > 0:
            Jw = J * sw[:, None]
            try:
                cov = np.linalg.inv(Jw.T @ Jw) * sse / dfe
                half = stats.t.ppf(0.975, dfe) * np.sqrt(np.maximum(
                    np.diag(cov), 0))
                bounds = np.vstack([coef - half, coef + half])
            except np.linalg.LinAlgError:
                bounds = np.full((2, p), np.nan)
        f = cfit(kind, key, names, formula, fn, coef, bounds)
        f._dfe, f._sse, f._J, f._w = dfe, sse, J, sw
        output = Struct(numobs=n, numparam=p, residuals=r.reshape(-1, 1),
                        Jacobian=J, exitflag=exitflag, algorithm=algorithm,
                        iterations=iterations)
        out = (f, gof, output)
        return out[:nargout] if nargout >= 2 else f

    def f_coeffvalues(self, f):
        return self._op_poly_out(np.asarray(_as_cfit(f, "coeffvalues")._values))

    def f_coeffnames(self, f):
        names = _as_cfit(f, "coeffnames")._names
        return Cell(list(names), rows=len(names))

    def f_confint(self, f, level=0.95):
        """2×p bounds on the coefficients at the given confidence level."""
        from scipy import stats
        f = _as_cfit(f, "confint")
        level = float(_scalar(level))
        if not 0 < level < 1:
            raise MatlabError("The confidence level must be between 0 and 1.")
        p = f._values.size
        if f._dfe <= 0:
            return np.full((2, p), np.nan)
        Jw = f._J * f._w[:, None]
        try:
            cov = np.linalg.inv(Jw.T @ Jw) * f._sse / f._dfe
        except np.linalg.LinAlgError:
            return np.full((2, p), np.nan)
        half = stats.t.ppf(1 - (1 - level) / 2, f._dfe) * np.sqrt(
            np.maximum(np.diag(cov), 0))
        return np.vstack([f._values - half, f._values + half])
