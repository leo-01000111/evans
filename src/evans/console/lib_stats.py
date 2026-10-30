"""
Statistics and linear algebra.
==============================
Descriptive statistics, distributions, factorisations, random integers.

A mixin of :class:`.matlab_runtime._Library`: each ``f_<name>`` method is
the MATLAB function ``<name>``. It is imported by :mod:`.matlab_runtime`
just before ``_Library`` is defined, so the helpers above that line can be
imported from it by name; anything defined further down is reached through
the module (``_mr._sprintf``) at call time. Import :mod:`.matlab_runtime` first, never this module on
its own: the two import each other.

Shapes follow MATLAB: a statistic of a vector (row or column) is a scalar;
of a matrix, one value per column (a row); ``dim`` picks the dimension.
"""

from __future__ import annotations

import time
import warnings

import numpy as np

from . import matlab_runtime as _mr  # noqa: F401
from .matlab_runtime import (
    MatlabError,
    Struct,
    _as2d,
    _float_array,
    _nargout,
    _normalise,
    _numel,
    _shape,
)

# ──────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────

def _out(a):
    """A MATLAB-shaped result: 1×1 a number, 1×n a row."""
    a = np.asarray(a)
    if a.dtype.kind == "c":
        a = np.real_if_close(a)
    if a.ndim == 0:
        return a.item()
    if a.ndim == 2 and a.size == 1:
        return a.reshape(-1)[0].item()
    return _normalise(a)


def _matrix(x, name: str = "") -> np.ndarray:
    """A numeric input as a float (or complex) 2-D array."""
    if isinstance(x, str):
        raise MatlabError(f"{name}: the input must be numeric.")
    a = _float_array(np.asarray(x if x is not None else np.zeros((0, 0))))
    if a.dtype == bool:
        a = a.astype(float)
    return _as2d(a)


def _square(x, name: str) -> np.ndarray:
    A = _matrix(x, name)
    if A.shape[0] != A.shape[1]:
        raise MatlabError("Matrix must be square.", f"MATLAB:{name}:square")
    return A


def _quietly(fn, A: np.ndarray) -> np.ndarray:
    """
    ``scipy.linalg.logm`` or ``sqrtm`` without its accuracy chatter.

    Up to SciPy 1.15 they took ``disp=False`` and returned ``(result,
    error estimate)``; later releases dropped the argument and return the
    result alone, warning instead of printing. Both are handled.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        try:
            result = fn(A, disp=False)
        except TypeError:
            return fn(A)
    return result[0] if isinstance(result, tuple) else result


def _axis_of(x, dim) -> int:
    """MATLAB's working dimension as a numpy axis of ``_as2d(x)``."""
    if dim is not None and not (isinstance(dim, np.ndarray) and dim.size == 0):
        d = float(np.asarray(dim).reshape(-1)[0])
        if d < 1 or d != int(d):
            raise MatlabError("Dimension argument must be a positive "
                              "integer scalar.")
        return int(d) - 1
    r, _ = _shape(x)
    return 1 if r == 1 else 0


def _is_dim_arg(v) -> bool:
    return not isinstance(v, str) and v is not None and _numel(v) == 1


def _flag(v, default):
    """A 0/1 flag argument; ``[]`` means the default."""
    if v is None or isinstance(v, np.ndarray) and v.size == 0:
        return default
    return float(np.asarray(v).reshape(-1)[0])


def _columns(fn, x, dim, empty=np.nan):
    """
    Apply ``fn(column) -> value`` along MATLAB's working dimension, giving
    a row for a matrix, a scalar for a vector. Past dimension 2, ``fn`` is
    applied to each element alone.
    """
    A = _matrix(x)
    axis = _axis_of(x, dim)
    if A.size == 0 and dim is None:
        return fn(np.zeros(0)) if empty is None else empty
    if axis >= 2:
        return _out(np.vectorize(lambda v: fn(np.array([v])),
                                 otypes=[float])(A))
    M = A if axis == 0 else A.T
    vals = np.array([fn(M[:, j]) for j in range(M.shape[1])])
    out = vals.reshape(1, -1) if axis == 0 else vals.reshape(-1, 1)
    return _out(out)


def _strings(args):
    """Split trailing option strings off positional arguments."""
    pos, opts = [], []
    for a in args:
        (opts if isinstance(a, str) else pos).append(a)
    return pos, [o.lower() for o in opts]


def _name_values(args, allowed: dict, fn: str) -> dict:
    """``'Name', value`` pairs, names case-insensitive."""
    if len(args) % 2:
        raise MatlabError(f"{fn}: name-value arguments must come in pairs.")
    out = {}
    for name, value in zip(args[::2], args[1::2]):
        if not isinstance(name, str) or name.lower() not in allowed:
            raise MatlabError(f"{fn}: Evans does not support the option "
                              f"'{name}'.")
        out[allowed[name.lower()]] = value
    return out


def _tcdf(t, df):
    from scipy import stats
    return stats.t.cdf(t, df)


def _tinv(p, df):
    from scipy import stats
    return stats.t.ppf(p, df)


def _percentiles(col: np.ndarray, p: np.ndarray, method: str) -> np.ndarray:
    """MATLAB's sorted-data percentiles (p in 0..100), NaN removed."""
    x = np.sort(col[~np.isnan(col)])
    n = x.size
    if n == 0:
        return np.full(p.shape, np.nan)
    if n == 1:
        return np.full(p.shape, x[0])
    k = np.arange(1, n + 1)
    if method == "midpoint":
        pos = 100 * (k - 0.5) / n
    elif method == "inclusive":
        pos = 100 * (k - 1) / (n - 1)
    else:                                       # exclusive
        pos = 100 * k / (n + 1)
    return np.interp(p, pos, x)


def _window(k, fn: str) -> tuple[int, int]:
    """MATLAB's moving window: ``k`` or ``[kb kf]`` → (back, forward)."""
    w = np.asarray(k, float).reshape(-1)
    if w.size == 1:
        k = w[0]
        if k != int(k) or k < 1:
            raise MatlabError(f"{fn}: Evans supports only a positive integer "
                              f"window length (or [kb kf]).")
        k = int(k)
        return (k // 2, k // 2 - 1) if k % 2 == 0 else ((k - 1) // 2,) * 2
    if w.size == 2:
        if np.any(w < 0) or np.any(w != np.round(w)):
            raise MatlabError(f"{fn}: Evans supports only non-negative "
                              f"integer [kb kf] windows.")
        return int(w[0]), int(w[1])
    raise MatlabError(f"{fn}: the window must be a scalar or a two-element "
                      f"vector [kb kf].")


def _moving(x, k, rest, fn: str, median: bool, default_nan: str = "include"):
    """movmean / movmedian, with MATLAB's 'shrink' endpoints by default."""
    pos, rest = [], list(rest)
    while rest and not isinstance(rest[0], str):
        pos.append(rest.pop(0))
    if len(pos) > 1:
        raise MatlabError(f"{fn}: too many input arguments.")
    dim = pos[0] if pos else None
    nan = default_nan
    endpoints = "shrink"
    while rest:
        opt = rest.pop(0)
        low = opt.lower()
        if low in ("includenan", "includemissing"):
            nan = "include"
        elif low in ("omitnan", "omitmissing"):
            nan = "omit"
        elif low == "endpoints" and rest:
            endpoints = rest.pop(0)
            if isinstance(endpoints, str):
                endpoints = endpoints.lower()
                if endpoints not in ("shrink", "discard"):
                    raise MatlabError(f"{fn}: Evans supports 'Endpoints' "
                                      f"'shrink', 'discard' or a fill value.")
            else:
                endpoints = float(np.asarray(endpoints).reshape(-1)[0])
        else:
            raise MatlabError(f"{fn}: Evans does not support the option "
                              f"'{opt}'.")
    kb, kf = _window(k, fn)
    A = _matrix(x)
    if A.size == 0:
        return np.zeros((0, 0))
    axis = _axis_of(x, dim)
    if axis >= 2:
        return _out(A)
    M = A if axis == 0 else A.T                   # work down the columns
    real_nan = np.isnan(M)
    width = kb + kf + 1
    pad = ((kb, kf), (0, 0))
    vals = np.pad(np.where(real_nan, 0.0, M), pad)
    inside = np.pad(np.ones(M.shape, bool), pad)
    nans = np.pad(real_nan, pad)
    view = np.lib.stride_tricks.sliding_window_view
    W, In, N = (view(a, width, axis=0) for a in (vals, inside, nans))
    use = In & ~N
    with warnings.catch_warnings(), np.errstate(invalid="ignore",
                                                divide="ignore"):
        warnings.simplefilter("ignore", RuntimeWarning)
        if median:
            out = np.nanmedian(np.where(use, W, np.nan), axis=2)
        else:
            out = (W * use).sum(axis=2) / use.sum(axis=2)
    if nan == "include":
        out[N.any(axis=2)] = np.nan
    full = In.all(axis=2)[:, 0]
    if endpoints == "discard":
        out = out[full]
    elif not isinstance(endpoints, str):
        out[~full] = endpoints
    out = out if axis == 0 else out.T
    if out.size == 0:
        return np.zeros((0, 0))
    return _out(out)


# ──────────────────────────────────────────────────────────────
#  The library
# ──────────────────────────────────────────────────────────────

class StatsLibrary:
    """var, cov, svd, randi and the rest."""

    # ── descriptive statistics ──────────────────────────────────

    def f_var(self, x, w=None, dim=None, *rest):
        """``var(x)``, ``var(x, w)``, ``var(x, w, dim)``, ``'all'``, ``'omitnan'``."""
        opts = []
        if isinstance(dim, str):
            opts.append(dim.lower())
            dim = None
        opts += [r.lower() for r in rest if isinstance(r, str)]
        if isinstance(w, str):
            opts.append(w.lower())
            w = None
        if any(not isinstance(r, str) for r in rest):
            raise MatlabError("Too many input arguments.")
        if w is not None and _numel(w) > 1:
            raise MatlabError("var: Evans does not support a weight vector; "
                              "use 0 or 1.")
        w = _flag(w, 0)
        if w not in (0, 1):
            raise MatlabError("W must be 0, 1, or a vector of nonnegative "
                              "weights.")
        omit = False
        for o in opts:
            if o == "all":
                x, dim = _matrix(x).reshape(-1, 1), None
            elif o in ("omitnan", "omitmissing"):
                omit = True
            elif o not in ("includenan", "includemissing"):
                raise MatlabError(f"var: Evans does not support the option "
                                  f"'{o}'.")

        def v(col):
            if omit:
                col = col[~np.isnan(col)]
            n = col.size
            if n == 0:
                return np.nan
            d = col - col.mean()
            ss = float(np.sum(np.abs(d) ** 2))
            return ss / (n if (w == 1 or n == 1) else n - 1)
        return _columns(v, x, dim)

    @_nargout
    def f_mode(self, x, dim=None, nargout=1):
        """``mode(x)``, ``[M, F] = mode(x)``: the smallest of tied values."""
        if nargout > 2:
            raise MatlabError("mode: Evans does not support the third output "
                              "C.")
        if isinstance(dim, str):
            raise MatlabError(f"mode: Evans does not support the option "
                              f"'{dim}'.")

        def pick(col):
            col = col[~np.isnan(col)]
            if col.size == 0:
                return (np.nan, 0.0)
            vals, counts = np.unique(col, return_counts=True)
            i = int(np.argmax(counts))          # first: the smallest value
            return (float(vals[i]), float(counts[i]))
        if _numel(x) == 0 and dim is None:
            return (np.nan, 0) if nargout == 2 else np.nan
        m = _columns(lambda c: pick(c)[0], x, dim)
        if nargout == 2:
            return m, _columns(lambda c: pick(c)[1], x, dim)
        return m

    def f_cov(self, x, *args):
        """``cov(A)``, ``cov(x, y)``, ``cov(..., w)``."""
        pos, opts = _strings(args)
        if opts:
            raise MatlabError(f"cov: Evans does not support the option "
                              f"'{opts[0]}'.")
        w, y = 0, None
        if len(pos) == 2:
            y, w = pos
        elif len(pos) == 1:
            p = pos[0]
            if _numel(p) == 1 and _numel(x) != 1 and float(
                    np.asarray(p).reshape(-1)[0]) in (0, 1):
                w = p
            else:
                y = p
        elif len(pos) > 2:
            raise MatlabError("Too many input arguments.")
        w = _flag(w, 0)
        if w not in (0, 1):
            raise MatlabError("W must be 0 or 1.")
        A = _matrix(x)
        if y is not None:
            B = _matrix(y)
            if A.size != B.size:
                raise MatlabError("X and Y must have the same number of "
                                  "elements.")
            A = np.column_stack([A.reshape(-1, order="F"),
                                 B.reshape(-1, order="F")])
        elif A.shape[0] == 1:
            A = A.T
        n = A.shape[0]
        if n == 0:
            return np.nan
        D = A - A.mean(axis=0)
        C = D.conj().T @ D / (n if (w == 1 or n == 1) else n - 1)
        return _out(C)

    @_nargout
    def f_corrcoef(self, x, *args, nargout=1):
        """``R = corrcoef(A)``, ``corrcoef(x, y)``, ``[R, P] = corrcoef(...)``."""
        if nargout > 2:
            raise MatlabError("corrcoef: Evans supports the outputs R and P "
                              "only.")
        pos, opts = _strings(args)
        if opts:
            raise MatlabError(f"corrcoef: Evans does not support the option "
                              f"'{opts[0]}'.")
        A = _matrix(x)
        if pos:
            B = _matrix(pos[0])
            if A.size != B.size:
                raise MatlabError("X and Y must have the same number of "
                                  "elements.")
            A = np.column_stack([A.reshape(-1, order="F"),
                                 B.reshape(-1, order="F")])
        elif A.shape[0] == 1:
            A = A.T
        n = A.shape[0]
        D = A - A.mean(axis=0)
        C = D.conj().T @ D
        d = np.sqrt(np.real(np.diag(C)))
        with np.errstate(invalid="ignore", divide="ignore"):
            R = C / np.outer(d, d)
        R = np.real_if_close(R)
        if np.isrealobj(R):
            R = np.clip(R, -1, 1)
        np.fill_diagonal(R, np.where(np.isnan(np.diag(R)), np.nan, 1.0))
        if nargout < 2:
            return _out(R)
        with np.errstate(invalid="ignore", divide="ignore"):
            r = np.abs(R)
            t = r * np.sqrt((n - 2) / (1 - r ** 2))
            P = 2 * _tcdf(-t, n - 2)
        np.fill_diagonal(P, 1.0)
        return _out(R), _out(P)

    def _prctile(self, fn, x, p, args, scale):
        dim, method = None, "midpoint"
        args = list(args)
        if args and not isinstance(args[0], str):
            dim = args.pop(0)
        nv = _name_values(args, {"method": "method"}, fn)
        if "method" in nv:
            method = str(nv["method"]).lower()
            method = {"exact": "midpoint"}.get(method, method)
            if method not in ("midpoint", "inclusive", "exclusive"):
                raise MatlabError(f"{fn}: Evans supports 'Method' 'midpoint' "
                                  f"(or 'exact'), 'inclusive' and "
                                  f"'exclusive'.")
        if isinstance(p, str):
            raise MatlabError(f"{fn}: Evans does not support '{p}'.")
        pv = np.asarray(p, float)
        pr, pc = _shape(p)
        pct = pv.reshape(-1) * scale
        if np.any(np.isnan(pct)) or np.any(pct < 0) or np.any(pct > 100):
            raise MatlabError("P must be a scalar or a vector of percent "
                              "values between 0 and 100." if scale == 1 else
                              "P must be a scalar or a vector of cumulative "
                              "probabilities between 0 and 1.")
        A = _matrix(x)
        xr, xc = _shape(x)
        vector = (xr == 1 or xc == 1) and dim is None
        if vector:
            out = _percentiles(A.reshape(-1), pct, method)
            return _out(out.reshape(pr, pc) if pv.ndim else out[0])
        axis = _axis_of(x, dim)
        if axis >= 2:
            return _out(A)
        M = A if axis == 0 else A.T
        cols = [_percentiles(M[:, j], pct, method) for j in range(M.shape[1])]
        out = np.column_stack(cols) if cols else np.zeros((pct.size, 0))
        return _out(out if axis == 0 else out.T)

    def f_prctile(self, x, p, *args):
        """``prctile(X, p)``, p in 0..100; MATLAB's 'midpoint' method."""
        return self._prctile("prctile", x, p, args, 1)

    def f_quantile(self, x, p, *args):
        """``quantile(X, p)``, p in 0..1; ``quantile(X, N)`` for N evenly
        spaced probabilities."""
        if not isinstance(p, str) and _numel(p) == 1:
            n = float(np.asarray(p).reshape(-1)[0])
            if n > 1 and n == int(n):
                p = np.arange(1, int(n) + 1) / (n + 1)
        return self._prctile("quantile", x, p, args, 100)

    def _moment(self, fn, x, flag, dim, kurt: bool):
        if isinstance(flag, str) or isinstance(dim, str):
            raise MatlabError(f"{fn}: Evans does not support string options.")
        flag = _flag(flag, 1)
        if flag not in (0, 1):
            raise MatlabError(f"{fn}: the flag must be 0 or 1.")

        def m(col):
            col = col[~np.isnan(col)]
            n = col.size
            if n == 0:
                return np.nan
            d = col - col.mean()
            m2 = np.mean(d ** 2)
            with np.errstate(invalid="ignore", divide="ignore"):
                if kurt:
                    k = np.mean(d ** 4) / m2 ** 2
                    if flag == 0:
                        if n < 4:
                            return np.nan
                        k = 3 + (n - 1) / ((n - 2) * (n - 3)) * (
                            (n + 1) * k - 3 * (n - 1))
                    return float(k)
                s = np.mean(d ** 3) / m2 ** 1.5
                if flag == 0:
                    if n < 3:
                        return np.nan
                    s = s * np.sqrt(n * (n - 1)) / (n - 2)
                return float(s)
        return _columns(m, x, dim)

    def f_skewness(self, x, flag=None, dim=None):
        """``skewness(X)`` (biased), ``skewness(X, 0)`` (bias-corrected)."""
        return self._moment("skewness", x, flag, dim, kurt=False)

    def f_kurtosis(self, x, flag=None, dim=None):
        """``kurtosis(X)`` (biased), ``kurtosis(X, 0)`` (bias-corrected)."""
        return self._moment("kurtosis", x, flag, dim, kurt=True)

    def f_movmean(self, x, k, *rest):
        return _moving(x, k, rest, "movmean", median=False)

    def f_movmedian(self, x, k, *rest):
        return _moving(x, k, rest, "movmedian", median=True)

    def f_smoothdata(self, x, *args):
        """``smoothdata(A, method, window)``: an explicit window only."""
        args = list(args)
        dim = None
        if args and not isinstance(args[0], str):
            dim = args.pop(0)
        method = "movmean"
        if args and isinstance(args[0], str) and args[0].lower() not in (
                "omitnan", "includenan", "omitmissing", "includemissing",
                "smoothingfactor", "samplepoints", "endpoints"):
            method = args.pop(0).lower()
        if method in ("gaussian", "lowess", "loess", "rlowess", "rloess",
                      "sgolay"):
            raise MatlabError(f"smoothdata: Evans does not support the "
                              f"'{method}' method yet; use 'movmean' or "
                              f"'movmedian'.")
        if method not in ("movmean", "movmedian"):
            raise MatlabError(f"smoothdata: unknown method '{method}'.")
        if not args or isinstance(args[0], str):
            raise MatlabError("smoothdata: Evans needs the window length, as "
                              "in smoothdata(A, 'movmean', k); MATLAB's "
                              "default window heuristic is not supported.")
        window = args.pop(0)
        rest = ([dim] if dim is not None else []) + args
        for o in args:
            if isinstance(o, str) and o.lower() in ("smoothingfactor",
                                                    "samplepoints"):
                raise MatlabError(f"smoothdata: Evans does not support the "
                                  f"option '{o}'.")
        return _moving(x, window, rest, "smoothdata",
                       median=(method == "movmedian"), default_nan="omit")

    def f_detrend(self, x, n=1, *rest):
        """``detrend(x)``, ``detrend(x, 0)``/``'constant'``, ``detrend(x, n)``."""
        if rest:
            raise MatlabError("detrend: Evans does not support breakpoints or "
                              "options.")
        if isinstance(n, str):
            low = n.lower()
            if low not in ("constant", "linear"):
                raise MatlabError(f"detrend: Evans does not support "
                                  f"'{n}'.")
            n = 0 if low == "constant" else 1
        n = float(np.asarray(n).reshape(-1)[0])
        if n < 0 or n != int(n):
            raise MatlabError("detrend: the degree must be a non-negative "
                              "integer.")
        n = int(n)
        A = _matrix(x)
        if A.size == 0:
            return np.zeros((0, 0))
        if np.any(np.isnan(A)):
            raise MatlabError("detrend: Evans does not support data with "
                              "NaN.")
        row = A.shape[0] == 1
        M = A.T if row else A
        m = M.shape[0]
        t = np.arange(m) / max(m - 1, 1)
        V = np.vander(t, n + 1)
        coef, *_ = np.linalg.lstsq(V, M, rcond=None)
        out = M - V @ coef
        return _out(out.T if row else out)

    # ── distributions and tests ─────────────────────────────────

    @staticmethod
    def _elementwise(fn, *args):
        arrs = [np.asarray(a, float) if not isinstance(a, np.ndarray)
                or a.dtype.kind != "c" else a for a in args]
        try:
            shape = np.broadcast_shapes(*(a.shape for a in arrs))
        except ValueError:
            raise MatlabError("Requires non-scalar arguments to match in "
                              "size.") from None
        with np.errstate(invalid="ignore", divide="ignore"):
            out = fn(*np.broadcast_arrays(*arrs))
        return _out(np.asarray(out, float).reshape(shape))

    def f_normpdf(self, x, mu=0, sigma=1):
        from scipy import stats

        def pdf(x, mu, s):
            return np.where(s > 0, stats.norm.pdf(x, mu, np.where(s > 0, s, 1)),
                            np.nan)
        return self._elementwise(pdf, x, mu, sigma)

    def f_normcdf(self, x, mu=0, sigma=1, tail=None):
        from scipy import stats
        if isinstance(mu, str):
            tail, mu = mu, 0
        elif isinstance(sigma, str):
            tail, sigma = sigma, 1
        upper = False
        if tail is not None:
            if not isinstance(tail, str) or tail.lower() not in ("upper",
                                                                 "lower"):
                raise MatlabError("normcdf: the last argument must be "
                                  "'upper'.")
            upper = tail.lower() == "upper"

        def cdf(x, mu, s):
            ok = np.where(s > 0, s, 1)
            v = stats.norm.sf(x, mu, ok) if upper else stats.norm.cdf(x, mu,
                                                                      ok)
            return np.where(s > 0, v, np.nan)
        return self._elementwise(cdf, x, mu, sigma)

    def f_norminv(self, p, mu=0, sigma=1):
        from scipy import stats

        def inv(p, mu, s):
            v = stats.norm.ppf(p, mu, np.where(s > 0, s, 1))
            return np.where(s > 0, v, np.nan)
        return self._elementwise(inv, p, mu, sigma)

    @_nargout
    def f_ttest(self, x, *args, nargout=1):
        """``[h, p, ci, stats] = ttest(x, m | y, 'Alpha', a, 'Tail', t)``."""
        args = list(args)
        m, y = 0.0, None
        if args and not isinstance(args[0], str):
            second = args.pop(0)
            if _numel(second) == 1 and _numel(x) != 1:
                m = float(np.asarray(second).reshape(-1)[0])
            else:
                y = second
        nv = _name_values(args, {"alpha": "alpha", "tail": "tail",
                                 "dim": "dim"}, "ttest")
        alpha = float(nv.get("alpha", 0.05))
        if not 0 < alpha < 1:
            raise MatlabError("ALPHA must be a scalar between 0 and 1.")
        tail = nv.get("tail", "both")
        tail = {"both": "both", "right": "right", "left": "left"}.get(
            str(tail).lower()) if isinstance(tail, str) else \
            {0: "both", 1: "right", -1: "left"}.get(int(tail))
        if tail is None:
            raise MatlabError("TAIL must be 'both', 'right', or 'left'.")
        X = _matrix(x)
        if y is not None:
            Y = _matrix(y)
            if X.shape != Y.shape:
                raise MatlabError("The data in a paired t-test must be the "
                                  "same size.")
            X = X - Y
        axis = _axis_of(x, nv.get("dim"))
        if axis >= 2:
            raise MatlabError("ttest: Evans works along dimension 1 or 2.")
        M = X if axis == 0 else X.T
        res = []
        for j in range(M.shape[1]):
            c = M[:, j]
            c = c[~np.isnan(c)]
            n = c.size
            df = max(n - 1, 0)
            mean = c.mean() if n else np.nan
            sd = c.std(ddof=1) if n > 1 else (0.0 if n == 1 else np.nan)
            with np.errstate(invalid="ignore", divide="ignore"):
                se = sd / np.sqrt(n)
                t = (mean - m) / se
            if tail == "both":
                p = 2 * _tcdf(-abs(t), df)
                crit = _tinv(1 - alpha / 2, df) * se
                ci = (mean - crit, mean + crit)
            elif tail == "right":
                p = _tcdf(-t, df)
                ci = (mean - _tinv(1 - alpha, df) * se, np.inf)
            else:
                p = _tcdf(t, df)
                ci = (-np.inf, mean + _tinv(1 - alpha, df) * se)
            h = np.nan if np.isnan(p) else float(p <= alpha)
            res.append((h, float(p), ci, float(t), float(df), float(sd)))

        def pack(k):
            v = np.array([r[k] for r in res], float)
            return _out(v.reshape(1, -1) if axis == 0 else v.reshape(-1, 1))
        h = pack(0)
        if nargout <= 1:
            return h
        out = [h, pack(1)]
        if nargout >= 3:
            ci = np.array([r[2] for r in res], float).T     # 2 × k
            out.append(_out(ci if axis == 0 else ci.T))
        if nargout >= 4:
            out.append(Struct(tstat=pack(3), df=pack(4), sd=pack(5)))
        return tuple(out[:nargout])

    @_nargout
    def f_regress(self, y, X, alpha=0.05, nargout=1):
        """``[b, bint, r, rint, stats] = regress(y, X, alpha)``."""
        from scipy import linalg, stats
        yv = _matrix(y).reshape(-1, 1) if 1 in _matrix(y).shape else None
        if yv is None:
            raise MatlabError("Y must be a vector and must have the same "
                              "number of rows as X.")
        Xm = _matrix(X)
        if Xm.shape[0] != yv.shape[0]:
            raise MatlabError("The number of rows in Y must equal the number "
                              "of rows in X.")
        alpha = float(alpha)
        keep = ~(np.isnan(yv[:, 0]) | np.isnan(Xm).any(axis=1))
        yk, Xk = yv[keep], Xm[keep]
        n, ncol = Xk.shape
        Q, R, perm = linalg.qr(Xk, mode="economic", pivoting=True)
        diag = np.abs(np.diag(R))
        tol = max(n, ncol) * np.spacing(diag[0]) if diag.size else 0
        p = int(np.sum(diag > tol))
        Q, R, perm = Q[:, :p], R[:p, :p], perm[:p]
        b = np.zeros((ncol, 1))
        b[perm] = linalg.solve_triangular(R, Q.T @ yk)
        if nargout <= 1:
            return _out(b)
        nu = max(0, n - p)
        yhat = Xk @ b
        r = yk - yhat
        rmse = np.linalg.norm(r) / np.sqrt(nu) if nu else np.nan
        bint = np.zeros((ncol, 2))
        tval = _tinv(1 - alpha / 2, nu)
        Rinv = linalg.solve_triangular(R, np.eye(p))
        se = np.sqrt(np.sum(Rinv ** 2, axis=1)) * rmse
        bint[perm, 0] = b[perm, 0] - tval * se
        bint[perm, 1] = b[perm, 0] + tval * se
        out = [_out(b), _out(bint)]
        rfull = np.full((yv.shape[0], 1), np.nan)
        rfull[keep] = r
        out.append(_out(rfull))
        if nargout >= 4:
            hat = np.sum(np.abs(Q) ** 2, axis=1)
            ok = ~(np.abs(hat - 1) < np.sqrt(np.finfo(float).eps))
            hat[~ok] = 0
            rint = np.full((yv.shape[0], 2), np.nan)
            if nu > 1:
                rr = r[:, 0]
                with np.errstate(invalid="ignore", divide="ignore"):
                    si = np.sqrt(np.maximum(0, (nu * rmse ** 2 - rr ** 2 /
                                                (1 - hat)) / (nu - 1)))
                ser = np.sqrt(1 - hat) * si
                ser[~ok] = np.inf
                tv = _tinv(1 - alpha / 2, nu - 1)
                rint[keep] = np.column_stack([rr - tv * ser, rr + tv * ser])
            out.append(_out(rint))
        if nargout >= 5:
            rss = np.linalg.norm(yhat - yk.mean()) ** 2
            tss = np.linalg.norm(yk - yk.mean()) ** 2
            r2 = rss / tss
            F = (rss / (p - 1)) / rmse ** 2 if p > 1 else np.nan
            prob = stats.f.sf(F, p - 1, nu) if p > 1 else np.nan
            out.append(np.array([r2, F, prob, rmse ** 2]))
        return tuple(out[:nargout])

    # ── factorisations ──────────────────────────────────────────

    @_nargout
    def f_svd(self, a, *opts, nargout=1):
        """``s = svd(A)``, ``[U, S, V] = svd(A)``, ``'econ'``, ``0``, ``'vector'``."""
        A = _matrix(a)
        econ = zero = vector = matrix = False
        for o in opts:
            if isinstance(o, str):
                low = o.lower()
                if low == "econ":
                    econ = True
                elif low == "vector":
                    vector = True
                elif low == "matrix":
                    matrix = True
                else:
                    raise MatlabError(f"svd: unknown option '{o}'.")
            elif _numel(o) == 1 and float(np.asarray(o).reshape(-1)[0]) == 0:
                zero = True
            else:
                raise MatlabError("Use svd(X,0) or svd(X,'econ') for economy "
                                  "size decomposition.")
        m, n = A.shape
        if nargout <= 1:
            s = np.linalg.svd(A, compute_uv=False).reshape(-1, 1)
            if matrix:
                k = min(m, n) if (econ or zero and m > n) else None
                S = np.zeros((m, n)) if k is None else np.zeros((k, k))
                S[:s.size, :s.size] = np.diag(s[:, 0])
                return _out(S)
            return _out(s)
        if econ or (zero and m > n):
            U, s, Vh = np.linalg.svd(A, full_matrices=False)
            S = np.diag(s)
        else:
            U, s, Vh = np.linalg.svd(A, full_matrices=True)
            S = np.zeros((m, n))
            S[:s.size, :s.size] = np.diag(s)
        S = s.reshape(-1, 1) if vector else S
        return tuple(_out(v) for v in (U, S, Vh.conj().T))[:nargout]

    @_nargout
    def f_qr(self, a, *opts, nargout=1):
        """``[Q, R] = qr(A)``, ``[Q, R, P] = qr(A)``, ``qr(A, 0)``, ``'econ'``."""
        from scipy import linalg
        A = _matrix(a)
        econ = False
        as_vector = None
        for o in opts:
            if isinstance(o, str):
                low = o.lower()
                if low == "econ":
                    econ = True
                elif low in ("vector", "matrix"):
                    as_vector = low == "vector"
                else:
                    raise MatlabError(f"qr: unknown option '{o}'.")
            elif _numel(o) == 1 and float(np.asarray(o).reshape(-1)[0]) == 0:
                econ, as_vector = True, True if as_vector is None else \
                    as_vector
            else:
                raise MatlabError("qr: use qr(A, 0) or qr(A, 'econ').")
        if as_vector is None:
            as_vector = False
        mode = "economic" if econ else "full"
        if nargout <= 1:
            R = linalg.qr(A, mode="r")[0]
            if econ:
                R = R[:min(A.shape), :]
            return _out(R)
        if nargout == 2:
            Q, R = linalg.qr(A, mode=mode)
            return _out(Q), _out(R)
        Q, R, piv = linalg.qr(A, mode=mode, pivoting=True)
        P = (piv + 1.0) if as_vector else np.eye(A.shape[1])[:, piv]
        return _out(Q), _out(R), _out(P)

    @_nargout
    def f_lu(self, a, *opts, nargout=1):
        """``[L, U] = lu(A)`` (L row-permuted), ``[L, U, P] = lu(A)``."""
        from scipy import linalg
        A = _matrix(a)
        vector = False
        for o in opts:
            if isinstance(o, str) and o.lower() in ("vector", "matrix"):
                vector = o.lower() == "vector"
            else:
                raise MatlabError(f"lu: Evans does not support the option "
                                  f"{o!r}.")
        if A.size == 0:
            e = np.zeros(A.shape)
            return (e,) * max(nargout, 1) if nargout > 1 else e
        Pm, L, U = linalg.lu(A)          # A = Pm L U, so P = Pm' in P*A = L*U
        if nargout <= 1:
            m, n = A.shape
            Y = np.zeros((m, n), dtype=np.result_type(L, U))
            Y[:U.shape[0], :] = U
            Y[:, :L.shape[1]] += np.tril(L, -1)
            return _out(Y)
        if nargout == 2:
            return _out(Pm @ L), _out(U)
        P = Pm.T
        if vector:
            P = np.argmax(P, axis=1) + 1.0
        return _out(L), _out(U), _out(P)

    @_nargout
    def f_chol(self, a, *opts, nargout=1):
        """``R = chol(A)``, ``[R, p] = chol(A)``, ``chol(A, 'lower')``."""
        from scipy.linalg import lapack
        lower = False
        for o in opts:
            if isinstance(o, str) and o.lower() in ("upper", "lower"):
                lower = o.lower() == "lower"
            else:
                raise MatlabError(f"chol: Evans does not support the option "
                                  f"{o!r}.")
        A = _square(a, "chol")
        potrf = lapack.zpotrf if np.iscomplexobj(A) else lapack.dpotrf
        c, info = potrf(A, lower=lower, clean=1)
        if info < 0:
            raise MatlabError("chol: invalid input.")
        if info > 0:
            if nargout < 2:
                raise MatlabError("Matrix must be positive definite.",
                                  "MATLAB:posdef")
            q = int(info) - 1
            c = c[:q, :q]
            c = np.tril(c) if lower else np.triu(c)
            return (_out(c) if c.size else np.zeros((0, 0)), info)
        c = np.tril(c) if lower else np.triu(c)
        return (_out(c), 0) if nargout >= 2 else _out(c)

    def f_pinv(self, a, tol=None):
        A = _matrix(a)
        if A.size == 0:
            return np.zeros(A.shape[::-1])
        U, s, Vh = np.linalg.svd(A, full_matrices=False)
        if tol is None:
            tol = max(A.shape) * np.spacing(s.max() if s.size else 0.0)
        tol = float(tol)
        k = s > tol
        X = (Vh[k].conj().T / s[k]) @ U[:, k].conj().T
        return _out(X)

    def f_null(self, a, tol=None):
        if isinstance(tol, str):
            raise MatlabError("null: Evans does not support the rational "
                              "basis 'r'.")
        A = _matrix(a)
        m, n = A.shape
        if A.size == 0:
            return np.eye(n) if n else np.zeros((0, 0))
        _, s, Vh = np.linalg.svd(A, full_matrices=True)
        if tol is None:
            tol = max(m, n) * np.spacing(s.max())
        r = int(np.sum(s > float(tol)))
        Z = Vh.conj().T[:, r:]
        return Z if Z.shape[1] != 1 else _out(Z)

    def f_orth(self, a, tol=None):
        A = _matrix(a)
        m, n = A.shape
        if A.size == 0:
            return np.zeros((m, 0))
        U, s, _ = np.linalg.svd(A, full_matrices=False)
        if tol is None:
            tol = max(m, n) * np.spacing(s.max())
        r = int(np.sum(s > float(tol)))
        Q = U[:, :r]
        return Q if Q.shape[1] != 1 else _out(Q)

    def f_expm(self, a):
        from scipy import linalg
        return _out(linalg.expm(_square(a, "expm")))

    def f_logm(self, a):
        from scipy import linalg
        return _out(_quietly(linalg.logm, _square(a, "logm")))

    def f_sqrtm(self, a):
        from scipy import linalg
        return _out(_quietly(linalg.sqrtm, _square(a, "sqrtm")))

    def f_cond(self, a, p=2):
        A = _matrix(a)
        if A.size == 0:
            return 0
        if isinstance(p, str):
            if p.lower() not in ("fro", "inf"):
                raise MatlabError(f"cond: unknown norm '{p}'.")
            p = "fro" if p.lower() == "fro" else np.inf
        else:
            p = float(p)
        if p == 2:
            s = np.linalg.svd(A, compute_uv=False)
            return float(np.inf) if s.min() == 0 else float(s.max() / s.min())
        if A.shape[0] != A.shape[1]:
            raise MatlabError("A is rectangular. Use the 2 norm.")
        if p not in (1, np.inf, "fro"):
            raise MatlabError("cond: the norm must be 1, 2, Inf or 'fro'.")
        try:
            inv = np.linalg.inv(A)
        except np.linalg.LinAlgError:
            return float(np.inf)
        return float(np.linalg.norm(A, p) * np.linalg.norm(inv, p))

    # ── vector products and matrix shapes ───────────────────────

    def f_cross(self, a, b, dim=None):
        A, B = _matrix(a), _matrix(b)
        ra, ca = _shape(a)
        rb, cb = _shape(b)
        vec_a, vec_b = 1 in (ra, ca), 1 in (rb, cb)
        if dim is None and vec_a and vec_b and A.size == 3 and B.size == 3:
            out = np.cross(A.reshape(-1), B.reshape(-1))
            return out if ra == 1 and rb == 1 else out.reshape(-1, 1)
        if A.shape != B.shape:
            raise MatlabError("A and B must be of the same size.")
        if dim is None:
            axis = 0 if A.shape[0] == 3 else 1 if A.shape[1] == 3 else None
        else:
            axis = _axis_of(a, dim)
        if axis is None or axis > 1 or A.shape[axis] != 3:
            raise MatlabError("A and B must be of length 3 in the dimension "
                              "in which the cross product is taken.")
        return _out(np.cross(A, B, axis=axis))

    def f_dot(self, a, b, dim=None):
        A, B = _matrix(a), _matrix(b)
        ra, ca = _shape(a)
        rb, cb = _shape(b)
        if dim is None and 1 in (ra, ca) and 1 in (rb, cb):
            if A.size != B.size:
                raise MatlabError("A and B must be same size.")
            v = np.sum(np.conj(A.reshape(-1)) * B.reshape(-1))
            return _out(v)
        if A.shape != B.shape:
            raise MatlabError("A and B must be same size.")
        axis = _axis_of(a, dim)
        if axis >= 2:
            return _out(np.conj(A) * B)
        return _out(np.sum(np.conj(A) * B, axis=axis, keepdims=True))

    def f_triu(self, a, k=0):
        return _out(np.triu(_matrix(a), int(k)))

    def f_tril(self, a, k=0):
        return _out(np.tril(_matrix(a), int(k)))

    def f_circshift(self, a, k, dim=None):
        text = isinstance(a, str)
        A = np.array([ord(c) for c in a]).reshape(1, -1) if text else \
            _as2d(np.asarray(a))
        ks = np.asarray(k, float).reshape(-1)
        if np.any(ks != np.round(ks)):
            raise MatlabError("Invalid shift type: must be a finite, "
                              "nonsparse, real integer vector.")
        ks = ks.astype(int)
        if dim is not None:
            if ks.size != 1:
                raise MatlabError("Invalid shift type: must be a finite, "
                                  "nonsparse, real integer scalar when DIM "
                                  "is given.")
            axis = _axis_of(a, dim)
            out = A if axis >= 2 else np.roll(A, ks[0], axis=axis)
        elif ks.size == 1:
            r, _ = A.shape
            axis = 1 if r == 1 else 0
            out = np.roll(A, ks[0], axis=axis)
        else:                     # [r c ...]: dimensions past 2 have size 1
            out = A
            for ax, s in enumerate(ks[:2]):
                out = np.roll(out, s, axis=ax)
        if text:
            return "".join(chr(int(c)) for c in out.reshape(-1))
        return _out(out)

    @staticmethod
    def _size_vector(sz) -> list[int]:
        s = np.asarray(sz, float).reshape(-1)
        if s.size < 2 or np.any(s < 0) or np.any(s != np.round(s)):
            raise MatlabError("Size vector must have at least two elements "
                              "of non-negative integers.")
        return [int(v) for v in s]

    def f_sub2ind(self, sz, *subs):
        dims = self._size_vector(sz)
        if not subs:
            raise MatlabError("Not enough input arguments.")
        shape = np.shape(np.asarray(subs[0]))
        arrs = [np.asarray(s, float) for s in subs]
        if any(np.shape(s) != shape for s in arrs):
            raise MatlabError("The subscript vectors must all be of the same "
                              "size.")
        k = len(arrs)
        if k < len(dims):
            dims = dims[:k - 1] + [int(np.prod(dims[k - 1:]))]
        elif k > len(dims):
            dims = dims + [1] * (k - len(dims))
        ind = np.zeros(shape)
        stride = 1
        for s, d in zip(arrs, dims):
            if np.any(s < 1) or np.any(s > d) or np.any(s != np.round(s)):
                raise MatlabError("Out of range subscript.",
                                  "MATLAB:sub2ind:IndexOutOfRange")
            ind = ind + (s - 1) * stride
            stride *= d
        return _out(ind + 1)

    @_nargout
    def f_ind2sub(self, sz, ind, nargout=1):
        dims = self._size_vector(sz)
        k = np.asarray(ind, float)
        if np.any(k < 1) or np.any(k > np.prod(dims)) or np.any(
                k != np.round(k)):
            raise MatlabError("Index out of range.",
                              "MATLAB:ind2sub:IndexOutOfRange")
        n = max(nargout, 1)
        if n == 1:
            return _out(k) if isinstance(ind, np.ndarray) else _out(k)
        if n < len(dims):
            dims = dims[:n - 1] + [int(np.prod(dims[n - 1:]))]
        else:
            dims = dims + [1] * (n - len(dims))
        rest = k - 1
        out = []
        for d in dims[:-1]:
            out.append(_out(rest % d + 1))
            rest = rest // d
        out.append(_out(rest + 1))
        return tuple(out)

    # ── random numbers ──────────────────────────────────────────

    def f_randi(self, imax, *dims):
        lim = np.asarray(imax, float).reshape(-1)
        bad = ("The first input must be a positive scalar integer value "
               "IMAX, or two integer values [IMIN IMAX] with IMIN less than "
               "or equal to IMAX.")
        if lim.size == 1:
            lo, hi = 1.0, lim[0]
        elif lim.size == 2:
            lo, hi = lim
        else:
            raise MatlabError(bad)
        if lo != int(lo) or hi != int(hi) or hi < lo or (lim.size == 1
                                                         and hi < 1):
            raise MatlabError(bad)
        for d in dims:
            if isinstance(d, str) and d.lower() != "double":
                raise MatlabError(f"randi: Evans returns doubles only; "
                                  f"'{d}' is not supported.")
        r, c = self._dims(tuple(d for d in dims if not isinstance(d, str)))
        out = np.random.randint(int(lo), int(hi) + 1, size=(r, c)).astype(
            float)
        return _out(out)

    def f_randperm(self, n, k=None):
        n = float(np.asarray(n).reshape(-1)[0])
        if n < 0 or n != int(n):
            raise MatlabError("N must be a nonnegative integer.")
        n = int(n)
        if k is None:
            k = n
        k = float(np.asarray(k).reshape(-1)[0])
        if k < 0 or k != int(k):
            raise MatlabError("K must be a nonnegative integer.")
        if k > n:
            raise MatlabError("K must be less than or equal to N.")
        out = np.random.permutation(n)[:int(k)] + 1.0
        return _out(out.reshape(1, -1)) if out.size else np.zeros((1, 0))

    _rng_seed = 0

    @staticmethod
    def _rng_settings(seed) -> Struct:
        name, keys, pos, has_gauss, cached = np.random.get_state()
        state = np.concatenate([keys.astype(float),
                                [pos, has_gauss, cached]]).reshape(-1, 1)
        return Struct(Type="twister", Seed=seed, State=state)

    @_nargout
    def f_rng(self, *args, nargout=1):
        """``rng(seed)``, ``rng('default')``, ``rng('shuffle')``, ``s = rng``."""
        previous = self._rng_settings(StatsLibrary._rng_seed)
        if not args:
            return previous
        arg = args[0]
        if len(args) > 2:
            raise MatlabError("Too many input arguments.")
        if len(args) == 2:
            gen = args[1]
            if not isinstance(gen, str) or gen.lower() != "twister":
                raise MatlabError(f"rng: Evans has the 'twister' generator "
                                  f"only, not {gen!r}.")
        if isinstance(arg, Struct) and "State" in arg:
            state = np.asarray(arg["State"], float).reshape(-1)
            if state.size != 627:
                raise MatlabError("rng: these settings were not captured by "
                                  "Evans' rng.")
            np.random.set_state(("MT19937", state[:624].astype(np.uint32),
                                 int(state[624]), int(state[625]),
                                 float(state[626])))
            StatsLibrary._rng_seed = arg.get("Seed", 0)
        elif isinstance(arg, str):
            low = arg.lower()
            if low == "default":
                seed = 0
            elif low == "shuffle":
                seed = int(time.time() * 1e6) % 2 ** 32
            elif low == "twister":
                seed = 0
            else:
                raise MatlabError(f"rng: Evans does not support {arg!r}.")
            np.random.seed(seed)
            StatsLibrary._rng_seed = seed
        else:
            s = np.asarray(arg, float).reshape(-1)
            if s.size != 1 or s[0] < 0 or s[0] >= 2 ** 32 or s[0] != int(s[0]):
                raise MatlabError("First input must be a nonnegative integer "
                                  "seed less than 2^32, 'shuffle', 'default',"
                                  " or generator settings captured "
                                  "previously using S = RNG.")
            np.random.seed(int(s[0]))
            StatsLibrary._rng_seed = int(s[0])
        return previous if nargout >= 1 else None
