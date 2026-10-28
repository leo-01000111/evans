"""
Signal processing for measured data: filtfilt, FIR design, spectra,
resampling, correlation, windows.

Each test types the command as a user would and checks it against a value
from a closed form, an explicit DFT sum, or a reference algorithm written out
step by step in the test from MATLAB's documented procedure (never against
what Evans printed).
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy import signal as sps
from scipy.special import i0

from evans.console import Interpreter, set_figure_sink
from evans.console.figures import recording_sink


@pytest.fixture
def it():
    previous = set_figure_sink(recording_sink())
    yield Interpreter()
    set_figure_sink(previous)


def run(it, source: str):
    """Run MATLAB, insist it succeeded."""
    results = it.run_script(source, "matlab")
    failed = [r for r in results if r.error]
    assert not failed, f"{failed[0].source!r} → {failed[0].error}"


def error_of(it, source: str) -> str:
    """Run MATLAB that must fail; return the error text."""
    results = it.run_script(source, "matlab")
    failed = [r for r in results if r.error]
    assert failed, f"{source!r} ran without an error"
    return str(failed[0].error)


def val(it, name):
    return it.namespace[name]


def signal_of(n):
    k = np.arange(1, n + 1)
    return np.sin(0.3 * k) + 0.5 * np.cos(1.7 * k) + 0.01 * k


SIGNAL = "x = sin(0.3*(1:{n})) + 0.5*cos(1.7*(1:{n})) + 0.01*(1:{n});"


# ──────────────────────────────────────────────────────────────
#  A hand-built filtfilt, step by step as MATLAB's filtfilt.m does it
# ──────────────────────────────────────────────────────────────

def matlab_zi(b, a):
    """The steady-state initial conditions, MATLAB's sparse system."""
    n = len(b)
    M = np.zeros((n - 1, n - 1))
    M[:, 0] = a[1:]
    M[0, 0] += 1
    for i in range(1, n - 1):
        M[i - 1, i] = -1
        M[i, i] = 1
    rhs = b[1:] - b[0] * a[1:]
    return np.linalg.solve(M, rhs)


def hand_filtfilt(b, a, x):
    b = np.asarray(b, float) / a[0]
    a = np.asarray(a, float) / a[0]
    n = max(len(a), len(b))
    b = np.concatenate([b, np.zeros(n - len(b))])
    a = np.concatenate([a, np.zeros(n - len(a))])
    nfact = 3 * (n - 1)
    zi = matlab_zi(b, a)
    xt = np.concatenate([2 * x[0] - x[nfact:0:-1], x,
                         2 * x[-1] - x[-2:-nfact - 2:-1]])
    y, _ = sps.lfilter(b, a, xt, zi=zi * xt[0])
    y = y[::-1]
    y, _ = sps.lfilter(b, a, y, zi=zi * y[0])
    return y[::-1][nfact:-nfact]


# ──────────────────────────────────────────────────────────────
#  filtfilt
# ──────────────────────────────────────────────────────────────

def test_filtfilt_matches_hand_construction(it):
    """
    Pad 3·(nfilt−1) samples at each end by odd reflection, filter forwards
    from ``zi·xt(1)``, reverse, filter again, reverse, trim: filtfilt.m.
    """
    b, a = sps.butter(3, 0.2)
    run(it, SIGNAL.format(n=60) + "[b, a] = butter(3, 0.2); y = filtfilt(b, a, x);")
    y = val(it, "y")
    assert y.shape == (60,)                       # a row stays a row
    np.testing.assert_allclose(y, hand_filtfilt(b, a, signal_of(60)),
                               rtol=0, atol=1e-12)


def test_filtfilt_fir_and_matrix_columns(it):
    """An FIR filter (a = 1), and a matrix filtered column by column."""
    b = np.array([1, 2, 3, 2, 1]) / 9
    x = signal_of(40)
    run(it, SIGNAL.format(n=40) + "b = [1 2 3 2 1]/9; X = [x' 2*x'];"
        "Y = filtfilt(b, 1, X); yc = filtfilt(b, 1, x');")
    Y, yc = val(it, "Y"), val(it, "yc")
    ref = hand_filtfilt(b, [1.0], x)
    assert Y.shape == (40, 2) and yc.shape == (40, 1)
    np.testing.assert_allclose(Y[:, 0], ref, atol=1e-12)
    np.testing.assert_allclose(Y[:, 1], 2 * ref, atol=1e-12)
    np.testing.assert_allclose(yc[:, 0], ref, atol=1e-12)


def test_filtfilt_one_section_sos_equals_transfer_function(it):
    """
    For a single biquad, the SOS path pads 3·order = 3·2 samples, the
    same as the b/a path's 3·(3−1), so the two must agree; the gain g
    scales the numerator.
    """
    b, a = sps.butter(2, 0.3)
    run(it, SIGNAL.format(n=50) + "[b, a] = butter(2, 0.3);"
        "y1 = filtfilt([b/b(1) a], b(1), x); y2 = filtfilt(b, a, x);")
    np.testing.assert_allclose(val(it, "y1"), val(it, "y2"), atol=1e-12)
    np.testing.assert_allclose(val(it, "y2"),
                               hand_filtfilt(b, a, signal_of(50)), atol=1e-12)


def test_filtfilt_refuses_short_data(it):
    """MATLAB needs more than 3·order samples."""
    msg = error_of(it, "[b, a] = butter(4, 0.2); y = filtfilt(b, a, 1:12);")
    assert "3 times filter order" in msg


# ──────────────────────────────────────────────────────────────
#  fir1, fir2
# ──────────────────────────────────────────────────────────────

def test_fir1_closed_form(it):
    """
    fir1(2, 0.5): ideal taps 0.5·sinc(0.5·m), m = −1, 0, 1, i.e.
    [1/π, 1/2, 1/π]; times hamming(3) = [0.08, 1, 0.08]; scaled to sum 1.
    """
    run(it, "b = fir1(2, 0.5);")
    h = np.array([1 / np.pi, 0.5, 1 / np.pi]) * np.array([0.08, 1, 0.08])
    np.testing.assert_allclose(val(it, "b"), h / h.sum(), atol=1e-15)
    assert val(it, "b").shape == (3,)


@pytest.mark.parametrize("cmd, kwargs", [
    ("fir1(20, 0.3)", dict(cutoff=0.3)),
    ("fir1(20, 0.3, 'high')", dict(cutoff=0.3, pass_zero=False)),
    ("fir1(20, [0.2 0.5])", dict(cutoff=[0.2, 0.5], pass_zero=False)),
    ("fir1(20, [0.2 0.5], 'stop')", dict(cutoff=[0.2, 0.5])),
])
def test_fir1_against_firwin(it, cmd, kwargs):
    """scipy's firwin (Hamming, scale=True) is the same windowed design."""
    run(it, f"b = {cmd};")
    ref = sps.firwin(21, window="hamming", scale=True, **kwargs)
    np.testing.assert_allclose(val(it, "b"), ref, atol=1e-14)


def test_fir1_odd_highpass_raises_order_and_takes_window(it):
    """An odd-order highpass becomes one order higher, as MATLAB warns."""
    run(it, "b = fir1(5, 0.4, 'high'); c = fir1(6, 0.4, rectwin(7));")
    assert val(it, "b").size == 7
    np.testing.assert_allclose(val(it, "b"), sps.firwin(
        7, 0.4, pass_zero=False, window="hamming"), atol=1e-14)
    np.testing.assert_allclose(val(it, "c"), sps.firwin(
        7, 0.4, window="boxcar"), atol=1e-14)
    assert "window length" in error_of(it, "b = fir1(6, 0.4, hann(5));")
    assert "(0,1)" in error_of(it, "b = fir1(6, 1.2);")


def test_fir2_flat_response_is_a_windowed_delay(it):
    """
    Unity gain everywhere: the shifted grid inverts to a delta at the
    centre tap, and hamming(11) is 1 there, so b = [0 … 0 1 0 … 0].
    """
    run(it, "b = fir2(10, [0 1], [1 1]);")
    ref = np.zeros(11)
    ref[5] = 1
    np.testing.assert_allclose(val(it, "b"), ref, atol=1e-14)


def test_fir2_follows_matlab_grid(it):
    """
    fir2.m step by step: 513-point grid, segment ends at fix(f·513), a
    repeated breakpoint spread over lap = fix(512/25) = 20 points, linear
    phase, inverse FFT of the conjugate-symmetric spectrum, Hamming.
    """
    run(it, "b = fir2(30, [0 0.3 0.3 1], [1 1 0.2 0.2]);")
    f, m, nn, npt, lap = [0, .3, .3, 1], [1, 1, .2, .2], 31, 513, 20
    H = np.zeros(npt + 1)
    nb, H[1] = 1, m[0]
    for i in range(3):
        if f[i + 1] == f[i]:
            nb = math.ceil(nb - lap / 2)
            ne = nb + lap
        else:
            ne = math.floor(f[i + 1] * npt)
        for j in range(nb, ne + 1):
            inc = 0 if nb == ne else (j - nb) / (ne - nb)
            H[j] = inc * m[i + 1] + (1 - inc) * m[i]
        nb = ne + 1
    k = np.arange(npt)
    G = H[1:] * np.exp(-1j * np.pi * 15 * k / (npt - 1))
    full = np.concatenate([G, np.conj(G[-2:0:-1])])
    n = np.arange(full.size)
    ht = np.real(np.exp(2j * np.pi * np.outer(np.arange(nn), n) / full.size)
                 @ full) / full.size
    ham = 0.54 - 0.46 * np.cos(2 * np.pi * np.arange(nn) / (nn - 1))
    np.testing.assert_allclose(val(it, "b"), ht * ham, atol=1e-13)


def test_fir2_refusals(it):
    assert "0 and the last 1" in error_of(it, "b = fir2(10, [0.1 1], [1 1]);")
    assert "even order" in error_of(it, "b = fir2(9, [0 1], [1 1]);")


# ──────────────────────────────────────────────────────────────
#  designfilt
# ──────────────────────────────────────────────────────────────

def test_designfilt_fir_is_fir1(it):
    """CutoffFrequency 100 Hz at 1 kHz is Wn = 0.2; window method."""
    run(it, "d = designfilt('lowpassfir', 'FilterOrder', 10, "
        "'CutoffFrequency', 100, 'SampleRate', 1000); c = d.Coefficients;"
        + SIGNAL.format(n=60) + "y = filtfilt(d, x);")
    ref = sps.firwin(11, 0.2, window="hamming")
    np.testing.assert_allclose(val(it, "c"), ref, atol=1e-14)
    np.testing.assert_allclose(val(it, "y"),
                               hand_filtfilt(ref, [1.0], signal_of(60)),
                               atol=1e-12)


def test_designfilt_iir_zero_phase_interior(it):
    """
    Away from the ends (where only the padding differs), filtfilt(d, x)
    of a Butterworth design equals filtfilt(b, a, x) of butter(4, 0.2).
    """
    run(it, "d = designfilt('lowpassiir', 'FilterOrder', 4, "
        "'HalfPowerFrequency', 0.2);" + SIGNAL.format(n=400)
        + "y = filtfilt(d, x');")
    b, a = sps.butter(4, 0.2)
    ref = hand_filtfilt(b, a, signal_of(400))
    y = val(it, "y")
    assert y.shape == (400, 1)
    np.testing.assert_allclose(y[150:250, 0], ref[150:250], atol=1e-9)


def test_designfilt_refusals(it):
    assert "not 'cheby1'" in error_of(
        it, "d = designfilt('lowpassiir', 'FilterOrder', 4, "
            "'HalfPowerFrequency', 0.2, 'DesignMethod', 'cheby1');")
    assert "PassbandFrequency" in error_of(
        it, "d = designfilt('lowpassiir', 'PassbandFrequency', 0.2, "
            "'FilterOrder', 4, 'HalfPowerFrequency', 0.2);")
    assert "bandstopiir" in error_of(it, "d = designfilt('bandstopiir');")


# ──────────────────────────────────────────────────────────────
#  Spectra
# ──────────────────────────────────────────────────────────────

def dft(x, nfft):
    n = np.arange(len(x))
    k = np.arange(nfft)
    return np.exp(-2j * np.pi * np.outer(k, n) / nfft) @ x


def test_pwelch_defaults_by_explicit_dft(it):
    """
    N = 1000: segments of fix(1000/4.5) = 222, overlap 111, 8 of them,
    Hamming, nfft = 256; |DFT|² / (w'w), averaged, one-sided ×2 except DC
    and Nyquist, divided by 2π; f = 2πk/256, k = 0..128.
    """
    run(it, SIGNAL.format(n=1000) + "[p, f] = pwelch(x);")
    x = signal_of(1000)
    L, nov = 222, 111
    w = 0.54 - 0.46 * np.cos(2 * np.pi * np.arange(L) / (L - 1))
    S = sum(np.abs(dft(x[i * (L - nov):i * (L - nov) + L] * w, 256)) ** 2
            for i in range(8)) / (8 * (w @ w))
    P = S[:129].copy()
    P[1:128] *= 2
    p, f = val(it, "p"), val(it, "f")
    assert p.shape == (129, 1) and f.shape == (129, 1)
    np.testing.assert_allclose(p[:, 0], P / (2 * np.pi), rtol=1e-10)
    np.testing.assert_allclose(f[:, 0], 2 * np.pi * np.arange(129) / 256)


def test_pwelch_explicit_arguments_and_fs(it):
    """window 100, overlap 50, nfft 128, fs 1000 Hz: per Hz, f to fs/2."""
    run(it, SIGNAL.format(n=500) + "[p, f] = pwelch(x, 100, 50, 128, 1000);")
    x = signal_of(500)
    w = 0.54 - 0.46 * np.cos(2 * np.pi * np.arange(100) / 99)
    k = (500 - 50) // 50
    S = sum(np.abs(dft(x[i * 50:i * 50 + 100] * w, 128)) ** 2
            for i in range(k)) / (k * (w @ w))
    P = S[:65].copy()
    P[1:64] *= 2
    np.testing.assert_allclose(val(it, "p")[:, 0], P / 1000, rtol=1e-10)
    assert val(it, "f")[-1, 0] == pytest.approx(500)


def test_periodogram_parseval(it):
    """
    Rectangular window, nfft = 256 ≥ N = 200: Σ pxx·(2π/nfft) is the mean
    square of x (Parseval), and the DC bin is |Σx|²/(2πN).
    """
    run(it, SIGNAL.format(n=200) + "[p, w] = periodogram(x);")
    x = signal_of(200)
    p = val(it, "p")[:, 0]
    assert p.size == 129
    assert p.sum() * 2 * np.pi / 256 == pytest.approx(np.mean(x ** 2),
                                                      rel=1e-12)
    assert p[0] == pytest.approx(abs(x.sum()) ** 2 / (2 * np.pi * 200),
                                 rel=1e-12)


def test_pwelch_plots_with_no_outputs():
    """No outputs: a dB plot over normalised frequency, as freqz draws."""
    sink = recording_sink()
    previous = set_figure_sink(sink)
    try:
        run(Interpreter(), SIGNAL.format(n=300) + "pwelch(x)")
    finally:
        set_figure_sink(previous)
    spec = sink.last
    assert spec is not None and "Welch" in spec.title
    assert spec.traces[0].x[-1] == pytest.approx(1.0)


def test_spectrogram_columns_are_segment_dfts(it):
    """
    Window 64, overlap 32, nfft 64, fs 8: column k is the DFT of segment k
    times hamming(64), rows 0..32; t is the segment centre in seconds.
    """
    run(it, SIGNAL.format(n=300)
        + "[s, f, t] = spectrogram(x, 64, 32, 64, 8);")
    x = signal_of(300)
    w = 0.54 - 0.46 * np.cos(2 * np.pi * np.arange(64) / 63)
    s, f, t = val(it, "s"), val(it, "f"), val(it, "t")
    k = (300 - 32) // 32
    assert s.shape == (33, k) and f.shape == (33, 1) and t.shape == (k,)
    for c in (0, 3, k - 1):
        np.testing.assert_allclose(
            s[:, c], dft(x[c * 32:c * 32 + 64] * w, 64)[:33], atol=1e-10)
    np.testing.assert_allclose(t, (np.arange(k) * 32 + 32) / 8)
    np.testing.assert_allclose(f[:, 0], np.arange(33) * 8 / 64)


def test_spectrogram_needs_outputs(it):
    assert "outputs" in error_of(it, "spectrogram(randn(1, 500))")


# ──────────────────────────────────────────────────────────────
#  resample, decimate
# ──────────────────────────────────────────────────────────────

def hand_resample(x, p, q, N=10, beta=5.0):
    """resample.m written out: sinc·kaiser, delay alignment, zero-stuffing."""
    pq = max(p, q)
    L = 2 * N * pq + 1
    m = np.arange(L) - (L - 1) / 2
    w = i0(beta * np.sqrt(1 - (2 * np.arange(L) / (L - 1) - 1) ** 2)) / i0(beta)
    h = np.sin(np.pi * m / pq) / (np.pi * np.where(m == 0, 1, m))
    h[m == 0] = 1 / pq
    h = h * w
    h = p * h / h.sum()
    Lhalf = (L - 1) / 2
    nz = math.floor(q - Lhalf % q)
    h = np.concatenate([np.zeros(nz), h])
    delay = math.floor(math.ceil(Lhalf + nz) / q)
    up = np.zeros(len(x) * p)
    up[::p] = x
    y = np.convolve(up, h)[::q]
    Ly = math.ceil(len(x) * p / q)
    y = np.concatenate([y, np.zeros(Ly + delay)])
    return y[delay:delay + Ly]


@pytest.mark.parametrize("p, q", [(3, 2), (2, 3), (1, 4), (5, 1)])
def test_resample_matches_matlab_design(it, p, q):
    run(it, SIGNAL.format(n=50) + f"y = resample(x, {p}, {q});")
    y = val(it, "y")
    assert y.shape == (math.ceil(50 * p / q),)
    np.testing.assert_allclose(y, hand_resample(signal_of(50), p, q),
                               atol=1e-12)


def test_resample_identity_and_columns(it):
    """p = q: the filter is a single tap of 1, so x comes back."""
    run(it, SIGNAL.format(n=30) + "y = resample(x', 2, 2);")
    np.testing.assert_allclose(val(it, "y")[:, 0], signal_of(30), atol=1e-14)
    assert "positive integers" in error_of(it, "y = resample(1:10, 1.5, 2);")


def test_decimate_default_chebyshev(it):
    """
    cheby1(8, 0.05, 0.8/r), zero-phase filtered, then x(nbeg:r:end) with
    nbeg = r − (r·ceil(nd/r) − nd): nd = 103, r = 4 → nbeg = 3.
    """
    run(it, SIGNAL.format(n=103) + "y = decimate(x, 4); yc = decimate(x', 4);")
    b, a = sps.cheby1(8, 0.05, 0.2)
    ref = hand_filtfilt(b, a, signal_of(103))[2::4]
    np.testing.assert_allclose(val(it, "y"), ref, atol=1e-10)
    assert val(it, "yc").shape == (26, 1)
    assert "'fir'" in error_of(it, "y = decimate(1:100, 4, 'fir');")
    assert "resample" in error_of(it, "y = interp(1:10, 2);")


# ──────────────────────────────────────────────────────────────
#  xcorr, impz, grpdelay
# ──────────────────────────────────────────────────────────────

def lag_sum(x, y, m):
    return sum(x[n + m] * np.conj(y[n]) for n in range(len(y))
               if 0 <= n + m < len(x))


def test_xcorr_sums_and_shapes(it):
    """r(m) = Σ x(n+m)·y(n); lags a row; r shaped like x."""
    run(it, "[r, lags] = xcorr([1 2 3], [4 5 6]); rc = xcorr([1; 2; 3]);")
    x, y = [1, 2, 3], [4, 5, 6]
    np.testing.assert_allclose(val(it, "r"),
                               [lag_sum(x, y, m) for m in range(-2, 3)])
    np.testing.assert_array_equal(val(it, "lags"), [-2, -1, 0, 1, 2])
    assert val(it, "rc").shape == (5, 1)
    np.testing.assert_allclose(val(it, "rc")[:, 0], [3, 8, 14, 8, 3])


def test_xcorr_scaling_and_maxlag(it):
    """biased /N, unbiased /(N−|m|), coeff /r(0); maxlag pads with zeros."""
    run(it, "x = [1 -2 3 1]; a = xcorr(x, 'biased'); b = xcorr(x, 'unbiased');"
        "c = xcorr(x, 'coeff'); [d, l] = xcorr(x, 5); e = xcorr(x, [1 1]);")
    x = [1, -2, 3, 1]
    raw = np.array([lag_sum(x, x, m) for m in range(-3, 4)], float)
    np.testing.assert_allclose(val(it, "a"), raw / 4)
    np.testing.assert_allclose(val(it, "b"), raw / (4 - np.abs(np.arange(-3, 4))))
    np.testing.assert_allclose(val(it, "c"), raw / raw[3])
    assert val(it, "d").size == 11 and val(it, "d")[0] == 0
    np.testing.assert_array_equal(val(it, "l"), np.arange(-5, 6))
    np.testing.assert_allclose(val(it, "e"), [lag_sum(x, [1, 1, 0, 0], m)
                                              for m in range(-3, 4)])
    assert "different lengths" in error_of(it, "r = xcorr([1 2 3], [1 2], 'coeff');")


def test_impz_closed_form(it):
    """1/(1 − 0.5 z⁻¹): h(n) = 0.5ⁿ; FIR default length is length(b)."""
    run(it, "[h, t] = impz(1, [1 -0.5], 6); g = impz([1 2 3]);")
    np.testing.assert_allclose(val(it, "h")[:, 0], 0.5 ** np.arange(6))
    np.testing.assert_array_equal(val(it, "t")[:, 0], np.arange(6))
    np.testing.assert_array_equal(val(it, "g")[:, 0], [1, 2, 3])
    assert "impz(b, a, n)" in error_of(it, "h = impz(1, [1 -0.5]);")


def test_grpdelay_closed_forms(it):
    """
    One pole at p: τ(ω) = (p·cosω − p²)/(1 − 2p·cosω + p²); a symmetric
    FIR of length 5 delays every frequency by 2 samples.
    """
    run(it, "[gd, w] = grpdelay(1, [1 -0.6], 8); g2 = grpdelay([1 3 5 3 1], 1, 4);"
        "[g3, f] = grpdelay(1, [1 -0.6], 8, 100);")
    w = np.pi * np.arange(8) / 8
    p = 0.6
    ref = (p * np.cos(w) - p ** 2) / (1 - 2 * p * np.cos(w) + p ** 2)
    np.testing.assert_allclose(val(it, "gd")[:, 0], ref, atol=1e-12)
    np.testing.assert_allclose(val(it, "w")[:, 0], w)
    np.testing.assert_allclose(val(it, "g2")[:, 0], 2, atol=1e-12)
    np.testing.assert_allclose(val(it, "f")[:, 0], np.arange(8) * 100 / 16)


# ──────────────────────────────────────────────────────────────
#  Windows
# ──────────────────────────────────────────────────────────────

def cosine_window(n, coeffs):
    k = np.arange(n)
    return sum((-1) ** j * c * np.cos(2 * np.pi * j * k / (n - 1))
               for j, c in enumerate(coeffs))


@pytest.mark.parametrize("name, coeffs", [
    ("hann", (0.5, 0.5)), ("hamming", (0.54, 0.46)),
    ("blackman", (0.42, 0.5, 0.08))])
@pytest.mark.parametrize("n", [5, 8])
def test_cosine_windows(it, name, coeffs, n):
    """Symmetric: the formula over k/(n−1); periodic: n+1 points, last off."""
    run(it, f"w = {name}({n}); wp = {name}({n}, 'periodic');")
    w, wp = val(it, "w"), val(it, "wp")
    assert w.shape == (n, 1) and wp.shape == (n, 1)
    np.testing.assert_allclose(w[:, 0], cosine_window(n, coeffs), atol=1e-15)
    np.testing.assert_allclose(wp[:, 0], cosine_window(n + 1, coeffs)[:-1],
                               atol=1e-15)


def test_other_windows(it):
    """hanning drops the zero ends; kaiser is I0(β√(1−r²))/I0(β); etc."""
    run(it, "a = hanning(4); b = kaiser(6, 2.5); c = triang(4); d = triang(5);"
        "e = bartlett(5); f = rectwin(3); g = hann(1); h = kaiser(4);")
    np.testing.assert_allclose(val(it, "a")[:, 0],
                               0.5 * (1 - np.cos(2 * np.pi * np.arange(1, 5) / 5)))
    r = 2 * np.arange(6) / 5 - 1
    np.testing.assert_allclose(val(it, "b")[:, 0],
                               i0(2.5 * np.sqrt(1 - r ** 2)) / i0(2.5))
    np.testing.assert_allclose(val(it, "c")[:, 0], [0.25, 0.75, 0.75, 0.25])
    np.testing.assert_allclose(val(it, "d")[:, 0], [1, 2, 3, 2, 1] / np.array(3))
    np.testing.assert_allclose(val(it, "e")[:, 0], [0, 0.5, 1, 0.5, 0])
    np.testing.assert_array_equal(val(it, "f")[:, 0], [1, 1, 1])
    assert val(it, "g") == 1
    r = 2 * np.arange(4) / 3 - 1
    np.testing.assert_allclose(val(it, "h")[:, 0],
                               i0(0.5 * np.sqrt(1 - r ** 2)) / i0(0.5))


def test_window_by_handle_and_name(it):
    run(it, "a = window(@hann, 4); b = window('kaiser', 5, 3); c = hann(0);")
    np.testing.assert_allclose(val(it, "a")[:, 0], [0, 0.75, 0.75, 0])
    r = 2 * np.arange(5) / 4 - 1
    np.testing.assert_allclose(val(it, "b")[:, 0],
                               i0(3 * np.sqrt(1 - r ** 2)) / i0(3))
    assert val(it, "c").shape == (0, 1)
    assert "flattopwin" in error_of(it, "w = window('flattopwin', 8);")
