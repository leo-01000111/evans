"""
Signal processing for measured data.
====================================
Zero-phase filtering, FIR design, spectra, resampling, correlation, windows.

A mixin of :class:`.matlab_runtime._Library`: each ``f_<name>`` method is
the MATLAB function ``<name>``. It is imported by :mod:`.matlab_runtime`
just before ``_Library`` is defined, so the helpers above that line can be
imported from it by name; anything defined further down is reached through
the module (``_mr._sprintf``) at call time. Import :mod:`.matlab_runtime` first, never this module on
its own: the two import each other.

Each function follows the Signal Processing Toolbox's own algorithm (its
defaults, its edge handling, its scaling), not scipy's, wherever the two
differ: ``filtfilt`` pads by ``3·(nfilt−1)`` samples, ``fir2`` interpolates on
MATLAB's 513-point grid with its transition smoothing, ``resample`` designs
its Kaiser-windowed least-squares filter and lines up the output as
``resample.m`` does. Frequencies are normalised so that 1 is Nyquist.
"""

from __future__ import annotations

import math

import numpy as np

from . import matlab_runtime as _mr  # noqa: F401
from .figures import FigureSpec
from .matlab_runtime import (
    MatlabError,
    _is_function,
    _nargout,
    _normalise,
    _numel,
    _scalar,
)

# ──────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────


def _empty(x) -> bool:
    return x is None or (not isinstance(x, str) and _numel(x) == 0)


def _int(x, what: str = "The order") -> int:
    v = float(np.asarray(x, float).reshape(-1)[0])
    if not math.isfinite(v):
        raise MatlabError(f"{what} must be finite.")
    return int(round(v))


def _vector(x) -> np.ndarray:
    a = np.asarray(x)
    if a.dtype.kind in "biu":
        a = a.astype(float)
    return np.atleast_1d(a).reshape(-1)


def _is_row(x) -> bool:
    return np.ndim(x) == 1 or (np.ndim(x) == 2 and np.shape(x)[0] == 1)


def _column(a) -> np.ndarray:
    return np.asarray(a).reshape(-1, 1)


def _columns(x) -> tuple[np.ndarray, bool]:
    """``x`` as a matrix of columns, and whether it came in as a row."""
    if np.ndim(x) == 0:
        return np.asarray(x, float).reshape(1, 1), False
    a = np.asarray(x)
    if a.dtype.kind in "biu":
        a = a.astype(float)
    if _is_row(a):
        return a.reshape(-1, 1), True
    return a, False


def _back(y: np.ndarray, row: bool):
    """A column result back as a row when the input was one."""
    return _normalise(y.reshape(1, -1)) if row else _normalise(y)


def _nextpow2(n: int) -> int:
    return 0 if n <= 1 else (int(n) - 1).bit_length()


def _option(args, names) -> tuple[list, list[str]]:
    """Split trailing string flags (lower-cased) from the numbers."""
    numbers, words = [], []
    for a in args:
        if isinstance(a, str):
            words.append(a.lower())
        else:
            numbers.append(a)
    for w in words:
        if w not in names:
            raise MatlabError(f"Evans does not support the option '{w}' "
                              f"here.")
    return numbers, words


def _ba(b, a) -> tuple[np.ndarray, np.ndarray]:
    bb = _vector(b).astype(complex if np.iscomplexobj(b) else float)
    aa = _vector(a).astype(complex if np.iscomplexobj(a) else float)
    if not aa.size or aa[0] == 0:
        raise MatlabError("First denominator filter coefficient must be "
                          "non-zero.")
    return bb / aa[0], aa / aa[0]


# ── windows (MATLAB computes half and mirrors it) ──────────────

def _window_length(n) -> int:
    if _empty(n):
        raise MatlabError("Window length must be specified.")
    v = float(np.asarray(n, float).reshape(-1)[0])
    if v < 0:
        raise MatlabError("Order cannot be less than zero.")
    return int(round(v))


def _sym_cos(n: int, coeffs) -> np.ndarray:
    """gencoswin's symmetric generalised-cosine window, length n."""
    if n == 1:
        return np.ones(1)
    half = n // 2 if n % 2 == 0 else (n + 1) // 2
    x = np.arange(half) / (n - 1)
    w = np.zeros(half)
    for k, c in enumerate(coeffs):
        w = w + ((-1) ** k) * c * np.cos(2 * np.pi * k * x)
    tail = w[::-1] if n % 2 == 0 else w[-2::-1]
    return np.concatenate([w, tail])


def _cos_window(n, sflag, coeffs) -> np.ndarray:
    n = _window_length(n)
    flag = "symmetric" if sflag is None else str(sflag).lower()
    if flag not in ("symmetric", "periodic"):
        raise MatlabError("Sampling flag must be 'symmetric' or 'periodic'.")
    if n == 0:
        return np.zeros((0, 1))
    if flag == "periodic":
        w = _sym_cos(n + 1, coeffs)[:-1]
    else:
        w = _sym_cos(n, coeffs)
    return w


_HANN = (0.5, 0.5)
_HAMMING = (0.54, 0.46)
_BLACKMAN = (0.42, 0.5, 0.08)


def _hamming(n: int) -> np.ndarray:
    return _cos_window(n, None, _HAMMING).reshape(-1)


def _win_out(w):
    w = np.asarray(w, float)
    if w.size == 0:
        return np.zeros((0, 1))
    return _normalise(w.reshape(-1, 1))


# ── zero-phase filtering ───────────────────────────────────────

def _filtfilt_ba(b, a, X: np.ndarray) -> np.ndarray:
    """MATLAB's filtfilt down the columns of ``X``."""
    from scipy.signal import filtfilt
    b, a = _ba(b, a)
    nfilt = max(b.size, a.size)
    b = np.concatenate([b, np.zeros(nfilt - b.size)])
    a = np.concatenate([a, np.zeros(nfilt - a.size)])
    nfact = max(1, 3 * (nfilt - 1))
    if X.shape[0] <= nfact:
        raise MatlabError(f"Data must have length more than 3 times filter "
                          f"order ({nfact}).",
                          "signal:filtfilt:InvalidDimensionsDataShortFor"
                          "FiltOrder")
    if nfilt == 1:
        return X * (b[0] / a[0]) ** 2
    return filtfilt(b, a, X, axis=0, padtype="odd", padlen=nfact)


def _sos_order(sos: np.ndarray) -> int:
    from scipy.signal import sos2tf
    b, a = sos2tf(sos)

    def trimmed(p):
        nz = np.nonzero(np.abs(p) > 0)[0]
        return 0 if not nz.size else nz[-1] + 1
    return max(trimmed(b), trimmed(a)) - 1


def _filtfilt_sos(sos: np.ndarray, X: np.ndarray) -> np.ndarray:
    """
    MATLAB's filtfilt of an SOS matrix (scale values already folded in):
    each section in turn is run forwards and backwards over the signal
    padded by ``3·order`` samples (the order of the whole cascade).
    """
    from scipy.signal import filtfilt
    nfact = max(1, 3 * _sos_order(sos))
    if X.shape[0] <= nfact:
        raise MatlabError(f"Data must have length more than 3 times filter "
                          f"order ({nfact}).",
                          "signal:filtfilt:InvalidDimensionsDataShortFor"
                          "FiltOrder")
    Y = np.asarray(X, float)
    for row in sos:
        b, a = row[:3] / row[3], row[3:] / row[3]
        Y = filtfilt(b, a, Y, axis=0, padtype="odd", padlen=nfact)
    return Y


# ── FIR design ─────────────────────────────────────────────────

def _fir1(n: int, wn: np.ndarray, ftype: str | None, window, scale: bool):
    """MATLAB's fir1: windowed ideal response, then unity-gain scaling."""
    if np.any(wn <= 0) or np.any(wn >= 1):
        raise MatlabError("The cutoff frequencies must be within the "
                          "interval of (0,1).")
    if np.any(np.diff(wn) <= 0):
        raise MatlabError("The cutoff frequencies must be increasing.")
    nb = wn.size
    if ftype is None:
        ftype = "low" if nb == 1 else ("bandpass" if nb == 2 else "dc-0")
    ftype = {"lowpass": "low", "highpass": "high", "bandstop": "stop",
             "pass": "bandpass"}.get(ftype, ftype)
    if ftype in ("low", "high") and nb != 1:
        raise MatlabError(f"A '{ftype}' filter needs one cutoff frequency.")
    if ftype in ("bandpass", "stop") and nb != 2:
        raise MatlabError(f"A '{ftype}' filter needs two cutoff "
                          f"frequencies.")
    first_pass = ftype in ("low", "stop", "dc-1")
    nbands = nb + 1
    last_pass = bool((int(first_pass) + nbands - 1) % 2) == (not first_pass) \
        if False else ((nbands - 1) % 2 == 0) == first_pass
    L = n + 1
    if last_pass and L % 2 == 0:
        print("Warning: Odd order symmetric FIR filters must have a gain of "
              "zero at the Nyquist frequency. The order is being increased "
              "by 1.")
        L += 1
    if window is None:
        win = _hamming(L)
    else:
        win = _vector(window).astype(float)
        if win.size != L:
            raise MatlabError("The window length must be the same as the "
                              "filter length.")
    edges = np.concatenate([[0.0], wn, [1.0]])
    m = np.arange(L) - (L - 1) / 2
    h = np.zeros(L)
    first_band = None
    for k in range(nbands):
        passing = (k % 2 == 0) == first_pass
        if passing:
            lo, hi = edges[k], edges[k + 1]
            h += hi * np.sinc(hi * m) - lo * np.sinc(lo * m)
            if first_band is None:
                first_band = (lo, hi)
    h = h * win
    if scale:
        if first_pass:
            h = h / np.sum(h)
        else:
            f0 = 1.0 if first_band[1] == 1 else (first_band[0]
                                                 + first_band[1]) / 2
            h = h / abs(np.sum(h * np.exp(-1j * np.pi * np.arange(L) * f0)))
    return h


def _fir2(nn: int, f, m, npt, lap, win) -> np.ndarray:
    """fir2.m: interpolate on the grid, shift, inverse FFT, window."""
    nint = f.size - 1
    df = np.diff(f)
    npt = npt + 1                      # [dc 1 2 ... nyquist]
    H = np.zeros(npt + 1)              # 1-based, H[0] unused
    nb = 1
    H[1] = m[0]
    for i in range(nint):
        if df[i] == 0:
            nb = int(math.ceil(nb - lap / 2))
            ne = nb + lap
        else:
            ne = int(math.floor(f[i + 1] * npt))
        if nb < 1 or ne > npt:
            raise MatlabError("Too abrupt an amplitude change near end of "
                              "frequency interval.", "signal:fir2:SignalErr")
        j = np.arange(nb, ne + 1)
        inc = 0.0 if nb == ne else (j - nb) / (ne - nb)
        H[nb:ne + 1] = inc * m[i + 1] + (1 - inc) * m[i]
        nb = ne + 1
    H = H[1:]
    dt = 0.5 * (nn - 1)
    rad = -dt * 1j * np.pi * np.arange(npt) / (npt - 1)
    H = H * np.exp(rad)
    Hconj = np.concatenate([H, np.conj(H[npt - 2:0:-1])])
    ht = np.real(np.fft.ifft(Hconj))
    return ht[:nn] * win


# ── spectra ────────────────────────────────────────────────────

def _datawrap(xw: np.ndarray, nfft: int) -> np.ndarray:
    """Fold columns longer than nfft onto nfft samples (MATLAB datawrap)."""
    n = xw.shape[0]
    if n <= nfft:
        return xw
    k = -(-n // nfft)
    pad = np.zeros((k * nfft - n, xw.shape[1]), xw.dtype)
    return np.concatenate([xw, pad]).reshape(k, nfft, -1).sum(axis=0)


def _sided(P: np.ndarray, nfft: int, onesided: bool, double: bool):
    """Rows kept for the range, the one-sided ones doubled (not DC/Nyquist)."""
    if not onesided:
        return P
    keep = nfft // 2 + 1 if nfft % 2 == 0 else (nfft + 1) // 2
    P = P[:keep].copy()
    if double:
        stop = keep - 1 if nfft % 2 == 0 else keep
        P[1:stop] *= 2
    return P


def _freqs(nfft: int, fs, onesided: bool) -> np.ndarray:
    full = np.arange(nfft) * ((2 * np.pi if fs is None else fs) / nfft)
    if onesided:
        keep = nfft // 2 + 1 if nfft % 2 == 0 else (nfft + 1) // 2
        full = full[:keep]
    return full.reshape(-1, 1)


def _spectral_window(win, n_signal: int, default_rect: bool):
    """Window vector from [] / a length / a vector, and its length."""
    if _empty(win):
        if default_rect:
            return np.ones(n_signal)
        L = int(n_signal // 4.5)
        return _hamming(L)
    w = _vector(win).astype(float)
    if w.size == 1:
        return _hamming(_int(w[0], "The window length"))
    return w


class DigitalFilter:
    """What ``designfilt`` returns: a filter and how it was specified."""

    def __init__(self, response: str, impulse: str, order: int, fs,
                 b=None, sos=None) -> None:
        self.FrequencyResponse = response
        self.ImpulseResponse = impulse
        self.FilterOrder = order
        self.SampleRate = 2 if fs is None else fs
        self._b = b
        self._sos = sos

    @property
    def Coefficients(self):
        if self.ImpulseResponse == "fir":
            return _normalise(self._b.reshape(1, -1))
        raise MatlabError("Evans does not show the second-order sections of "
                          "an IIR designfilt filter, since it can't promise "
                          "MATLAB's grouping of them; use butter for [b, a].")

    def __repr__(self) -> str:
        return (f"  digitalFilter ({self.FrequencyResponse}, "
                f"{self.ImpulseResponse.upper()}, order "
                f"{self.FilterOrder})")


_DESIGNS = {
    "lowpassiir": ("lowpass", "iir"), "highpassiir": ("highpass", "iir"),
    "bandpassiir": ("bandpass", "iir"), "lowpassfir": ("lowpass", "fir"),
    "highpassfir": ("highpass", "fir"),
}


# ──────────────────────────────────────────────────────────────
#  The library
# ──────────────────────────────────────────────────────────────

class SignalLibrary:
    """filtfilt, fir1, pwelch, hann and the rest."""

    # ── windows ─────────────────────────────────────────────────

    def f_hann(self, n, sflag=None):
        return _win_out(_cos_window(n, sflag, _HANN))

    def f_hamming(self, n, sflag=None):
        return _win_out(_cos_window(n, sflag, _HAMMING))

    def f_blackman(self, n, sflag=None):
        return _win_out(_cos_window(n, sflag, _BLACKMAN))

    def f_hanning(self, n, sflag=None):
        """hanning: the Hann window without its zero end points."""
        n = _window_length(n)
        flag = "symmetric" if sflag is None else str(sflag).lower()
        if flag not in ("symmetric", "periodic"):
            raise MatlabError("Sampling flag must be 'symmetric' or "
                              "'periodic'.")
        if n == 0:
            return np.zeros((0, 1))
        if flag == "periodic":
            w = np.concatenate([[0.0], self._sym_hanning(n - 1)])
        else:
            w = self._sym_hanning(n)
        return _win_out(w)

    @staticmethod
    def _sym_hanning(n: int) -> np.ndarray:
        if n == 0:
            return np.zeros(0)
        half = n // 2 if n % 2 == 0 else (n + 1) // 2
        w = 0.5 * (1 - np.cos(2 * np.pi * np.arange(1, half + 1) / (n + 1)))
        return np.concatenate([w, w[::-1] if n % 2 == 0 else w[-2::-1]])

    def f_kaiser(self, n, beta=0.5):
        n = _window_length(n)
        if n == 0:
            return np.zeros((0, 1))
        return _win_out(np.kaiser(n, float(beta)))

    def f_rectwin(self, n):
        n = _window_length(n)
        return _win_out(np.ones(n))

    def f_triang(self, n):
        n = _window_length(n)
        if n == 0:
            return np.zeros((0, 1))
        if n % 2:
            w = 2 * np.arange(1, (n + 1) // 2 + 1) / (n + 1)
            w = np.concatenate([w, w[-2::-1]])
        else:
            w = (2 * np.arange(1, n // 2 + 1) - 1) / n
            w = np.concatenate([w, w[::-1]])
        return _win_out(w)

    def f_bartlett(self, n):
        n = _window_length(n)
        if n == 0:
            return np.zeros((0, 1))
        if n == 1:
            return 1
        w = 2 * np.arange(0, (n - 1) // 2 + 1) / (n - 1)
        w = np.concatenate([w, w[-2::-1] if n % 2 else w[::-1]])
        return _win_out(w)

    _WINDOWS = ("hann", "hamming", "blackman", "hanning", "kaiser",
                "rectwin", "triang", "bartlett")

    def f_window(self, fn, n, *args):
        if isinstance(fn, str):
            name = fn.lower()
            if name not in self._WINDOWS:
                raise MatlabError(f"Evans does not have the window "
                                  f"'{fn}'; it has "
                                  f"{', '.join(self._WINDOWS)}.")
            fn = getattr(self, "f_" + name)
        elif not _is_function(fn) and not callable(fn):
            raise MatlabError("The first input must be a window function "
                              "handle, such as @hann, or its name.")
        w = self.rt.call(fn, (n, *args), nargout=1)
        return _win_out(np.asarray(w, float).reshape(-1))

    # ── zero-phase filtering ───────────────────────────────────

    def f_filtfilt(self, b, a, x=None):
        if isinstance(b, DigitalFilter):
            if x is not None:
                raise MatlabError("Use filtfilt(d, x) with a designfilt "
                                  "filter.")
            X, row = _columns(a)
            Y = _filtfilt_ba(b._b, 1, X) if b.ImpulseResponse == "fir" \
                else _filtfilt_sos(b._sos, X)
            return _back(Y, row)
        if x is None:
            raise MatlabError("Not enough input arguments.")
        X, row = _columns(x)
        B = np.asarray(b, float)
        if B.ndim == 2 and B.shape[1] == 6 and (
                B.shape[0] > 1 or (B[0, 3] == 1 and _numel(a) <= 2)):
            sos = B.copy()
            g = _vector(a).astype(float)
            L = sos.shape[0]
            if g.size > L + 1:
                raise MatlabError(f"The scale values vector must have at "
                                  f"most {L + 1} elements.")
            if g.size == L + 1:
                sos[L - 1, :3] *= g[L]
            for k in range(min(g.size, L)):
                sos[k, :3] *= g[k]
            return _back(_filtfilt_sos(sos, X), row)
        if B.ndim == 2 and 1 not in B.shape:
            raise MatlabError("filtfilt needs b and a as vectors, or an SOS "
                              "matrix with six columns.")
        return _back(_filtfilt_ba(b, a, X), row)

    # ── FIR design ─────────────────────────────────────────────

    def f_fir1(self, n, wn, *args):
        ftype, window, scale = None, None, True
        for arg in args:
            if isinstance(arg, str):
                word = arg.lower()
                if word in ("scale", "noscale"):
                    scale = word == "scale"
                elif word in ("low", "high", "bandpass", "stop", "bandstop",
                              "dc-0", "dc-1", "lowpass", "highpass"):
                    ftype = word
                else:
                    raise MatlabError(f"Evans does not support the fir1 "
                                      f"option '{arg}'.")
            elif not _empty(arg):
                window = arg
        h = _fir1(_int(n), _vector(wn).astype(float), ftype, window, scale)
        return _normalise(h.reshape(1, -1))

    def f_fir2(self, n, f, m, *args):
        nn = _int(n) + 1
        ff = _vector(f).astype(float)
        mm = _vector(m).astype(float)
        if ff.size != mm.size:
            raise MatlabError("The frequency and magnitude vectors must be "
                              "the same length.")
        if ff.size < 2 or ff[0] != 0 or ff[-1] != 1:
            raise MatlabError("The first frequency must be 0 and the last "
                              "1.")
        if np.any(np.diff(ff) < 0):
            raise MatlabError("Frequencies must be non-decreasing.")
        if any(isinstance(a, str) for a in args):
            raise MatlabError("Evans does not support fir2's 'h' and 'd' "
                              "filter types.")
        npt = 512 if nn < 1024 else 2 ** _nextpow2(nn)
        lap = None
        win = None
        rest = list(args)
        if rest and _numel(rest[-1]) > 1:
            win = _vector(rest.pop()).astype(float)
        if rest and not _empty(rest[0]):
            npt = _int(rest[0], "npt")
        if len(rest) > 1 and not _empty(rest[1]):
            lap = _int(rest[1], "lap")
        if lap is None:
            lap = npt // 25
        if nn % 2 == 0 and mm[-1] != 0:
            raise MatlabError("An odd-order fir2 filter must have zero gain "
                              "at Nyquist; MATLAB raises the order by one "
                              "here, which Evans doesn't. Use an even "
                              "order.")
        if 2 * npt < nn:
            raise MatlabError("The number of grid points npt is too small "
                              "for this filter order.")
        if win is None:
            win = _hamming(nn)
        elif win.size != nn:
            raise MatlabError("The window length must be the same as the "
                              "filter length.")
        return _normalise(_fir2(nn, ff, mm, npt, lap, win).reshape(1, -1))

    def f_designfilt(self, response, *args):
        kind = str(response).lower()
        if kind not in _DESIGNS:
            raise MatlabError(f"Evans's designfilt supports "
                              f"{', '.join(repr(k) for k in _DESIGNS)}; "
                              f"not '{response}'.")
        if len(args) % 2:
            raise MatlabError("Specifications must come in name-value "
                              "pairs.")
        spec = {}
        for k in range(0, len(args), 2):
            spec[str(args[k]).lower()] = args[k + 1]
        shape, impulse = _DESIGNS[kind]
        if impulse == "iir":
            freq_names = (("halfpowerfrequency1", "halfpowerfrequency2")
                          if shape == "bandpass" else ("halfpowerfrequency",))
        else:
            freq_names = ("cutofffrequency",)
        allowed = {"filterorder", "samplerate", "designmethod", *freq_names}
        if impulse == "fir":
            allowed |= {"window"}
        unknown = [k for k in spec if k not in allowed]
        if unknown:
            raise MatlabError(f"Evans's designfilt('{kind}', ...) takes "
                              f"FilterOrder, {', '.join(freq_names)}, "
                              f"SampleRate and DesignMethod; it does not "
                              f"support '{unknown[0]}'.")
        missing = [k for k in ("filterorder", *freq_names) if k not in spec]
        if missing:
            raise MatlabError(f"designfilt('{kind}', ...) needs "
                              f"'FilterOrder' and "
                              f"'{', '.join(freq_names)}' (Evans doesn't "
                              f"design from other specification sets).")
        method = str(spec.get("designmethod",
                              "butter" if impulse == "iir" else "window"))
        if method.lower() != ("butter" if impulse == "iir" else "window"):
            raise MatlabError(f"Evans's designfilt supports DesignMethod "
                              f"'{'butter' if impulse == 'iir' else 'window'}'"
                              f" for '{kind}', not '{method}'.")
        if "window" in spec and str(spec["window"]).lower() != "hamming":
            raise MatlabError("Evans's designfilt supports the default "
                              "'hamming' window only.")
        order = _int(spec["filterorder"])
        if order < 1:
            raise MatlabError("FilterOrder must be a positive integer.")
        fs = None if _empty(spec.get("samplerate")) else float(
            spec["samplerate"])
        nyq = 1.0 if fs is None else fs / 2
        wn = np.array([float(spec[k]) for k in freq_names]) / nyq
        if np.any(wn <= 0) or np.any(wn >= 1):
            raise MatlabError("The frequencies must lie strictly between 0 "
                              "and the Nyquist frequency.")
        if impulse == "fir":
            if shape == "highpass" and order % 2:
                raise MatlabError("A highpass FIR filter must have an even "
                                  "FilterOrder.")
            b = _fir1(order, wn, "low" if shape == "lowpass" else "high",
                      None, True)
            return DigitalFilter(kind, "fir", order, fs, b=b)
        from scipy.signal import butter
        if shape == "bandpass":
            if order % 2:
                raise MatlabError("A bandpass IIR filter must have an even "
                                  "FilterOrder.")
            sos = butter(order // 2, wn, btype="bandpass", output="sos")
        else:
            sos = butter(order, float(wn[0]), btype=shape, output="sos")
        return DigitalFilter(kind, "iir", order, fs, sos=sos)

    # ── spectra ────────────────────────────────────────────────

    def _psd_plot(self, f, pxx, fs, title):
        x = f.reshape(-1) if fs is not None else f.reshape(-1) / np.pi
        with np.errstate(divide="ignore"):
            y = 10 * np.log10(np.asarray(pxx)[:, 0])
        spec = FigureSpec(
            "xy", title,
            "Frequency (Hz)" if fs is not None
            else "Normalized Frequency (×π rad/sample)",
            "Power/frequency (dB/Hz)" if fs is not None
            else "Power/frequency (dB/(rad/sample))")
        self.rt.figures.collect(spec.add(x, y))

    def _psd(self, X, win, noverlap, nfft, fs, words, name):
        complex_x = np.iscomplexobj(X)
        onesided = not complex_x
        if "twosided" in words:
            onesided = False
        if "onesided" in words:
            if complex_x:
                raise MatlabError("The 'onesided' range is not valid for "
                                  "complex input.")
            onesided = True
        L = win.size
        N = X.shape[0]
        if L > N:
            raise MatlabError("The length of the segments cannot be greater "
                              "than the length of the input signal.")
        if L < 1:
            raise MatlabError("The window must have at least one sample.")
        if noverlap >= L:
            raise MatlabError("The number of samples to overlap must be less "
                              "than the length of the segments.")
        if nfft is None:
            nfft = max(256, 2 ** _nextpow2(L))
        k = (N - noverlap) // (L - noverlap)
        U = float(win @ win)
        S = 0
        for i in range(k):
            seg = X[i * (L - noverlap): i * (L - noverlap) + L]
            Xf = np.fft.fft(_datawrap(seg * win[:, None], nfft), n=nfft,
                            axis=0)
            S = S + np.abs(Xf) ** 2
        S = S / (k * U)
        P = _sided(S, nfft, onesided, True)
        P = P / (2 * np.pi if fs is None else fs)
        return P, _freqs(nfft, fs, onesided)

    @staticmethod
    def _signal_matrix(x, name):
        if _empty(x):
            raise MatlabError(f"{name} needs a signal.")
        X, _ = _columns(x)
        return X

    @staticmethod
    def _nfft(v):
        if _empty(v):
            return None
        if _numel(v) > 1:
            raise MatlabError("Evans does not support a vector of "
                              "frequencies in place of nfft.")
        return _int(v, "nfft")

    @staticmethod
    def _fs(v):
        return None if _empty(v) else float(np.asarray(v).reshape(-1)[0])

    _PSD_WORDS = ("onesided", "twosided", "psd")

    @_nargout
    def f_pwelch(self, x, *args, nargout=1):
        nums, words = _option(args, self._PSD_WORDS)
        if len(nums) > 4:
            raise MatlabError("Too many input arguments.")
        nums += [None] * (4 - len(nums))
        X = self._signal_matrix(x, "pwelch")
        win = _spectral_window(nums[0], X.shape[0], False)
        noverlap = (int(win.size // 2) if _empty(nums[1])
                    else _int(nums[1], "noverlap"))
        fs = self._fs(nums[3])
        P, f = self._psd(X, win, noverlap, self._nfft(nums[2]), fs, words,
                         "pwelch")
        if nargout == 0:
            self._psd_plot(f, P, fs, "Welch Power Spectral Density Estimate")
            return None
        return (_normalise(P), f) if nargout >= 2 else _normalise(P)

    @_nargout
    def f_periodogram(self, x, *args, nargout=1):
        nums, words = _option(args, self._PSD_WORDS)
        if len(nums) > 3:
            raise MatlabError("Too many input arguments.")
        nums += [None] * (3 - len(nums))
        X = self._signal_matrix(x, "periodogram")
        win = _spectral_window(nums[0], X.shape[0], True)
        if win.size != X.shape[0]:
            raise MatlabError("The length of the window must equal the "
                              "length of the input.")
        nfft = self._nfft(nums[1])
        if nfft is None:
            nfft = max(256, 2 ** _nextpow2(X.shape[0]))
        fs = self._fs(nums[2])
        P, f = self._psd(X, win, 0, nfft, fs, words, "periodogram")
        if nargout == 0:
            self._psd_plot(f, P, fs, "Periodogram Power Spectral Density "
                                     "Estimate")
            return None
        return (_normalise(P), f) if nargout >= 2 else _normalise(P)

    @_nargout
    def f_spectrogram(self, x, *args, nargout=1):
        if nargout == 0:
            raise MatlabError("Evans can't draw a spectrogram yet; ask for "
                              "the outputs: [s, f, t] = spectrogram(...).")
        nums, words = _option(args, ("onesided", "twosided"))
        if len(nums) > 4:
            raise MatlabError("Too many input arguments.")
        nums += [None] * (4 - len(nums))
        if _empty(x) or not (_is_row(x) or np.shape(x)[1] == 1):
            raise MatlabError("spectrogram needs a vector signal.")
        xv = _vector(x)
        win = _spectral_window(nums[0], xv.size, False)
        L = win.size
        noverlap = int(L // 2) if _empty(nums[1]) else _int(nums[1],
                                                            "noverlap")
        if L > xv.size:
            raise MatlabError("The length of the segments cannot be greater "
                              "than the length of the input signal.")
        if noverlap >= L:
            raise MatlabError("The number of samples to overlap must be less "
                              "than the length of the segments.")
        nfft = self._nfft(nums[2]) or max(256, 2 ** _nextpow2(L))
        fs = self._fs(nums[3])
        onesided = not np.iscomplexobj(xv)
        if "twosided" in words:
            onesided = False
        if "onesided" in words:
            onesided = True
        k = (xv.size - noverlap) // (L - noverlap)
        starts = np.arange(k) * (L - noverlap)
        frames = np.stack([xv[s:s + L] * win for s in starts], axis=1)
        F = np.fft.fft(_datawrap(frames, nfft), n=nfft, axis=0)
        S = _sided(F, nfft, onesided, False)
        f = _freqs(nfft, fs, onesided)
        t = (starts + L / 2) / (1.0 if fs is None else fs)
        out = [_normalise(S), f, _normalise(t.reshape(1, -1))]
        if nargout >= 4:
            ps = _sided(np.abs(F) ** 2 / float(win @ win), nfft, onesided,
                        True) / (2 * np.pi if fs is None else fs)
            out.append(_normalise(ps))
        return tuple(out[:nargout]) if nargout >= 2 else out[0]

    # ── resampling ─────────────────────────────────────────────

    def f_resample(self, x, p, q, n=10, beta=5):
        from scipy.signal import upfirdn
        if _numel(p) != 1 or _numel(q) != 1:
            raise MatlabError("Evans's resample takes integer factors p and "
                              "q; it does not resample at given times.")
        pf, qf = float(np.asarray(p).reshape(-1)[0]), float(
            np.asarray(q).reshape(-1)[0])
        if pf <= 0 or qf <= 0 or pf != int(pf) or qf != int(qf):
            raise MatlabError("P and Q must be positive integers.")
        p, q = int(pf), int(qf)
        g = math.gcd(p, q)
        p, q = p // g, q // g
        if _numel(n) > 1:
            raise MatlabError("Evans does not support resample with your own "
                              "filter coefficients.")
        N = _int(n, "n")
        if N <= 0:
            raise MatlabError("Evans's resample needs n > 0 (MATLAB's n = 0 "
                              "nearest-neighbour form is not supported).")
        X, row = _columns(x)
        pqmax = max(p, q)
        L = 2 * N * pqmax + 1
        m = np.arange(L) - (L - 1) / 2
        # firls(L-1, [0 2fc 2fc 1], [1 1 0 0]) with no transition band is
        # the ideal response, the sinc, exactly.
        h = np.sinc(m / pqmax) / pqmax * np.kaiser(L, float(beta))
        h = p * h / np.sum(h)
        Lhalf = (L - 1) / 2
        Lx = X.shape[0]
        nz = int(math.floor(q - (Lhalf % q)))
        h = np.concatenate([np.zeros(nz), h])
        Lhalf += nz
        delay = int(math.floor(math.ceil(Lhalf) / q))
        nz1 = 0
        while math.ceil(((Lx - 1) * p + h.size + nz1) / q) - delay < \
                math.ceil(Lx * p / q):
            nz1 += 1
        h = np.concatenate([h, np.zeros(nz1)])
        y = upfirdn(h, X, p, q, axis=0)
        Ly = int(math.ceil(Lx * p / q))
        y = y[delay:delay + Ly]
        return _back(y, row)

    def f_decimate(self, x, r, *args):
        from scipy.signal import cheby1
        if any(isinstance(a, str) for a in args):
            if any(str(a).lower() == "fir" for a in args
                   if isinstance(a, str)):
                raise MatlabError("Evans does not support decimate's 'fir' "
                                  "option; the default Chebyshev filter "
                                  "is supported.")
            raise MatlabError("Unknown decimate option.")
        rf = float(np.asarray(r).reshape(-1)[0])
        if rf != int(rf) or rf < 1:
            raise MatlabError("Resampling rate R must be a positive integer.")
        r = int(rf)
        if _empty(x) or not (_is_row(x) or np.shape(x)[1] == 1):
            raise MatlabError("Input must be a vector.")
        row = _is_row(x)
        xv = _vector(x).astype(float)
        if r == 1:
            return x
        nfilt = 8 if not args else _int(args[0])
        if nfilt > 13:
            print("Warning: Using an IIR filter of order greater than 13 "
                  "may produce unreliable results.")
        rip = 0.05

        def mag_db(b, a, f):
            z = np.exp(1j * np.pi * f)
            h = np.polyval(b[::-1], 1 / z) / np.polyval(a[::-1], 1 / z)
            with np.errstate(divide="ignore"):
                return 20 * np.log10(abs(h))
        b, a = cheby1(nfilt, rip, 0.8 / r)
        while np.all(b == 0) or abs(mag_db(b, a, 0.8 / r) + rip) > 1e-6:
            nfilt -= 1
            if nfilt == 0:
                break
            b, a = cheby1(nfilt, rip, 0.8 / r)
        if nfilt == 0:
            raise MatlabError("Bad Chebyshev design, likely R is too big; "
                              "try mult. decimation (R=R1*R2).")
        y = _filtfilt_ba(b, a, xv.reshape(-1, 1)).reshape(-1)
        nd = xv.size
        nout = -(-nd // r)
        nbeg = r - (r * nout - nd)
        y = y[nbeg - 1:nd:r]
        return _normalise(y) if row else y.reshape(-1, 1)

    def f_interp(self, *args):
        raise MatlabError("Evans does not have interp (its intfilt-based "
                          "filter isn't reproduced exactly); use "
                          "resample(x, r, 1).")

    # ── correlation and filter analysis ────────────────────────

    @_nargout
    def f_xcorr(self, x, *args, nargout=1):
        rest = list(args)
        scale = "none"
        if rest and isinstance(rest[-1], str):
            scale = rest.pop().lower()
        if scale not in ("none", "biased", "unbiased", "coeff",
                         "normalized"):
            raise MatlabError(f"Unknown scale option '{scale}'.")
        for v in [x, *rest[:1]]:
            if not isinstance(v, str) and np.ndim(v) == 2 and \
                    1 not in np.shape(v):
                raise MatlabError("Evans's xcorr takes vectors; it does not "
                                  "correlate the columns of a matrix.")
        y = None
        maxlag = None
        if rest:
            if len(rest) == 1 and _numel(rest[0]) == 1 and _numel(x) > 1:
                maxlag = rest[0]
            else:
                y = rest[0]
                if len(rest) > 1:
                    maxlag = rest[1]
        xv = _vector(x)
        yv = xv if y is None else _vector(y)
        if scale != "none" and xv.size != yv.size:
            raise MatlabError("SCALEOPT must be 'none' when x and y have "
                              "different lengths.")
        N = max(xv.size, yv.size)
        xp = np.concatenate([xv, np.zeros(N - xv.size)])
        yp = np.concatenate([yv, np.zeros(N - yv.size)])
        full = np.correlate(xp, yp, "full")          # lags -(N-1) .. N-1
        if not (np.iscomplexobj(xv) or np.iscomplexobj(yv)):
            full = np.real(full).astype(float)
        lags_all = np.arange(-(N - 1), N)
        if scale == "biased":
            full = full / N
        elif scale == "unbiased":
            full = full / (N - np.abs(lags_all))
        elif scale in ("coeff", "normalized"):
            denom = math.sqrt(abs(np.vdot(xp, xp)) * abs(np.vdot(yp, yp)))
            full = full / denom if denom else full
        M = N - 1 if _empty(maxlag) else _int(maxlag, "MAXLAG")
        if M < 0:
            raise MatlabError("MAXLAG must be a nonnegative integer.")
        lags = np.arange(-M, M + 1)
        r = np.zeros(lags.size, full.dtype)
        inside = np.abs(lags) <= N - 1
        r[inside] = full[lags[inside] + N - 1]
        out = _normalise(r.reshape(1, -1)) if _is_row(x) else r.reshape(-1, 1)
        if _is_row(x) and r.size == 1:
            out = _scalar(r[0])
        if nargout >= 2:
            return out, _normalise(lags.reshape(1, -1).astype(float))
        return out

    @_nargout
    def f_impz(self, b, a=1, n=None, fs=None, nargout=1):
        from scipy.signal import lfilter
        bb, aa = _ba(b, a)
        if _empty(n):
            if aa.size > 1 and np.any(aa[1:] != 0):
                raise MatlabError("Evans needs the length for an IIR filter: "
                                  "impz(b, a, n).")
            idx = np.arange(bb.size)
        elif _numel(n) == 1:
            idx = np.arange(_int(n, "n"))
        else:
            idx = np.round(_vector(n).astype(float)).astype(int)
            if np.any(idx < 0):
                raise MatlabError("Evans's impz takes sample indices from 0 "
                                  "up.")
        count = int(idx.max()) + 1 if idx.size else 0
        imp = np.zeros(count)
        if count:
            imp[0] = 1
        h = lfilter(bb, aa, imp)[idx] if count else np.zeros(0)
        h = np.real_if_close(h)
        rate = 1.0 if _empty(fs) else float(fs)
        t = idx / rate
        if nargout == 0:
            spec = FigureSpec("xy", "Impulse Response",
                              "n (samples)" if _empty(fs) else "Time (s)",
                              "Amplitude")
            self.rt.figures.collect(spec.add(t, np.real(h), style="stem"))
            return None
        H = _column(h)
        return (H, _column(t)) if nargout >= 2 else H

    @_nargout
    def f_grpdelay(self, b, a=1, n=512, *rest, nargout=1):
        whole = any(isinstance(r, str) and r.lower() == "whole"
                    for r in rest)
        bad = [r for r in rest if isinstance(r, str) and r.lower() != "whole"]
        if bad:
            raise MatlabError(f"Unknown grpdelay option '{bad[0]}'.")
        numbers = [r for r in rest if not isinstance(r, str)]
        fs = self._fs(numbers[0]) if numbers else None
        bb, aa = _ba(b, a)
        if _numel(n) > 1:
            given = _vector(n).astype(float)
            w = given if fs is None else 2 * np.pi * given / fs
            freq = given
        else:
            count = 512 if _empty(n) else _int(n, "n")
            span = 2 * np.pi if whole else np.pi
            w = span * np.arange(count) / count
            freq = w if fs is None else w * fs / (2 * np.pi)
        c = np.convolve(bb, np.conj(aa[::-1]))
        k = np.arange(c.size)
        E = np.exp(-1j * np.outer(w, k))
        den = E @ c
        num = E @ (k * c)
        sing = np.abs(den) < 10 * np.finfo(float).eps
        if np.any(sing):
            print("Warning: The group delay is singular at some "
                  "frequencies; it is set to 0 there.")
        gd = np.where(sing, 0.0, np.real(num / np.where(sing, 1, den))) \
            - (aa.size - 1)
        gd[sing] = 0.0
        if nargout == 0:
            spec = FigureSpec(
                "xy", "Group delay",
                "Frequency (Hz)" if fs else
                "Normalized Frequency (×π rad/sample)",
                "Group delay (samples)")
            self.rt.figures.collect(
                spec.add(freq if fs else w / np.pi, gd))
            return None
        G = _column(gd)
        return (G, _column(freq)) if nargout >= 2 else G
