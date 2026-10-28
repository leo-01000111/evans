"""
Statistics and linear algebra (Phase 1).

Each test types the command as a user would and checks it against a value
worked out by hand, from a closed form, or by an independent route (a
property of the factorisation, or a different formula), never against what
Evans printed.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

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


def arr(it, name):
    return np.asarray(val(it, name))


# ──────────────────────────────────────────────────────────────
#  var, mode, cov, corrcoef
# ──────────────────────────────────────────────────────────────

def test_var_of_vector_matrix_and_dim(it):
    """
    [1 2 3 4]: squared deviations 2.25+0.25+0.25+2.25 = 5, so 5/3 with N−1
    and 5/4 with N. Columns of [1 2;3 5] are [1 3] (2) and [2 5] (4.5); along
    rows with w = 1, [1 2] gives 0.25 and [3 5] gives 1, as a column.
    """
    run(it, "a = var([1 2 3 4]); b = var([1 2 3 4]', 1); "
            "c = var([1 2;3 5]); d = var([1 2;3 5], 1, 2); e = var(7);")
    assert val(it, "a") == pytest.approx(5 / 3)
    assert val(it, "b") == pytest.approx(1.25)
    assert arr(it, "c").shape == (2,)
    assert arr(it, "c") == pytest.approx([2, 4.5])
    assert arr(it, "d").shape == (2, 1)
    assert arr(it, "d").ravel() == pytest.approx([0.25, 1])
    assert val(it, "e") == 0


def test_var_refuses_weight_vector(it):
    """A weight vector changes the answer; Evans refuses it."""
    assert "weight vector" in error_of(it, "var([1 2 3], [1 1 2])")


def test_mode_smallest_of_ties_and_frequency(it):
    """1 and 3 both appear twice in [3 1 1 3 2]: MATLAB picks the smaller."""
    run(it, "[m, f] = mode([3 1 1 3 2]); c = mode([1 2;1 3;2 3]);")
    assert val(it, "m") == 1
    assert val(it, "f") == 2
    assert arr(it, "c") == pytest.approx([1, 3])


def test_cov_vector_pair_and_matrix(it):
    """
    x = [1 2 3], y = [1 2 4]: var x = 1, var y = (16+1+25)/9/2 = 7/3, and
    cov = ((−1)(−4/3) + 0 + (1)(5/3))/2 = 1.5 — MATLAB's 2×2 matrix. The
    matrix [1 2;2 4;3 6] has a second column twice the first.
    """
    run(it, "c = cov([1 2 3], [1 2 4]); v = cov([1 2 3]); "
            "m = cov([1 2;2 4;3 6]); w = cov([1 2 3], 1);")
    assert arr(it, "c") == pytest.approx(np.array([[1, 1.5], [1.5, 7 / 3]]))
    assert val(it, "v") == pytest.approx(1)
    assert arr(it, "m") == pytest.approx(np.array([[1, 2], [2, 4]]))
    assert val(it, "w") == pytest.approx(2 / 3)


def test_corrcoef_and_p_value(it):
    """
    x = [1 2 3 4], y = [1 3 2 4]: Σdxdy = 4, Σdx² = Σdy² = 5, r = 0.8. With
    n − 2 = 2 degrees of freedom the t CDF is ½ + t/(2√(2+t²)), so
    p = 1 − |t|/√(2+t²) = 1 − r = 0.2 exactly.
    """
    run(it, "[R, P] = corrcoef([1 2 3 4], [1 3 2 4]);")
    assert arr(it, "R") == pytest.approx(np.array([[1, 0.8], [0.8, 1]]))
    assert arr(it, "P") == pytest.approx(np.array([[1, 0.2], [0.2, 1]]))


def test_corrcoef_refuses_bounds_outputs(it):
    assert "R and P" in error_of(it, "[R,P,L,U] = corrcoef([1 2 3],[3 1 2]);")


# ──────────────────────────────────────────────────────────────
#  prctile, quantile, skewness, kurtosis
# ──────────────────────────────────────────────────────────────

def test_prctile_midpoint_method(it):
    """
    MATLAB puts the k-th of n sorted values at 100(k−0.5)/n percent and
    interpolates: for [1 2 3 4] that is 12.5, 37.5, 62.5, 87.5, so the 50th
    is 2.5 and the 25th 1.5; below 12.5 is the minimum, above 87.5 the max.
    """
    run(it, "a = prctile([1 2 3 4], 50); b = prctile([1 2 3 4], 25); "
            "c = prctile([4 3 2 1]', [0 100]); d = prctile(1:4, [25; 50]); "
            "e = prctile([1 10;2 20;3 30;4 40], 50);")
    assert val(it, "a") == pytest.approx(2.5)
    assert val(it, "b") == pytest.approx(1.5)
    assert arr(it, "c") == pytest.approx([1, 4])
    assert arr(it, "d").shape == (2, 1)              # shaped like p
    assert arr(it, "d").ravel() == pytest.approx([1.5, 2.5])
    assert arr(it, "e") == pytest.approx([2.5, 25])


def test_prctile_inclusive_and_nan(it):
    """'inclusive' puts the k-th value at 100(k−1)/(n−1): 25% of 1..4 is 1.75.
    NaN is dropped: [1 NaN 3] behaves as [1 3]."""
    run(it, "a = prctile([1 2 3 4], 25, 'Method', 'inclusive'); "
            "b = prctile([1 NaN 3], 50);")
    assert val(it, "a") == pytest.approx(1.75)
    assert val(it, "b") == pytest.approx(2)


def test_quantile_probabilities_and_count(it):
    """quantile(x, 3) asks for p = 1/4, 2/4, 3/4 — the 25th, 50th, 75th."""
    run(it, "a = quantile([1 2 3 4], 0.25); b = quantile([1 2 3 4], 3);")
    assert val(it, "a") == pytest.approx(1.5)
    assert arr(it, "b") == pytest.approx([1.5, 2.5, 3.5])
    assert "between 0 and 1" in error_of(it, "quantile([1 2 3], 1.5)")


def test_skewness_and_kurtosis_by_hand(it):
    """
    [1 2 3 10]: mean 4, deviations −3 −2 −1 6, m2 = 12.5, m3 = 45,
    m4 = 348.5. Biased skewness m3/m2^1.5, kurtosis m4/m2²; the corrected
    forms are √(n(n−1))/(n−2)·g1 and 3 + (n−1)/((n−2)(n−3))((n+1)g2 − 3(n−1)).
    """
    run(it, "s = skewness([1 2 3 10]); s0 = skewness([1 2 3 10], 0); "
            "k = kurtosis([1 2 3 10]); k0 = kurtosis([1 2 3 10], 0); "
            "c = skewness([1 1;2 2;3 10]);")
    g1, g2, n = 45 / 12.5 ** 1.5, 348.5 / 12.5 ** 2, 4
    assert val(it, "s") == pytest.approx(g1)
    assert val(it, "s0") == pytest.approx(g1 * math.sqrt(n * (n - 1)) / (n - 2))
    assert val(it, "k") == pytest.approx(g2)
    assert val(it, "k0") == pytest.approx(
        3 + (n - 1) / ((n - 2) * (n - 3)) * ((n + 1) * g2 - 3 * (n - 1)))
    assert arr(it, "c")[0] == pytest.approx(0)       # 1 2 3 is symmetric
    assert arr(it, "c").shape == (2,)


# ──────────────────────────────────────────────────────────────
#  Moving windows, smoothdata, detrend
# ──────────────────────────────────────────────────────────────

def test_movmean_odd_even_and_shrink(it):
    """
    k = 3 on 1..5: the ends shrink to [1 2] and [4 5] (1.5, 4.5). k = 4
    takes two back and one forward: [1 2], [1 2 3], [1..4], [2..5], [3 4 5].
    """
    run(it, "a = movmean(1:5, 3); b = movmean(1:5, 4); "
            "c = movmean([1 2 3], [1 0]); d = movmean((1:5)', 3);")
    assert arr(it, "a") == pytest.approx([1.5, 2, 3, 4, 4.5])
    assert arr(it, "b") == pytest.approx([1.5, 2, 2.5, 3.5, 4])
    assert arr(it, "c") == pytest.approx([1, 1.5, 2.5])
    assert arr(it, "d").shape == (5, 1)


def test_movmedian_and_endpoint_options(it):
    """
    [4 1 3 2 5]' with k = 3: medians of [4 1], [4 1 3], [1 3 2], [3 2 5],
    [2 5] are 2.5, 3, 2, 3, 3.5. 'discard' keeps the three full windows.
    """
    run(it, "a = movmedian([4 1 3 2 5]', 3); "
            "b = movmean(1:5, 3, 'Endpoints', 'discard'); "
            "c = movmean([1 NaN 3], 3); d = movmean([1 NaN 3], 3, 'omitnan');")
    assert arr(it, "a").ravel() == pytest.approx([2.5, 3, 2, 3, 3.5])
    assert arr(it, "b") == pytest.approx([2, 3, 4])
    assert np.isnan(arr(it, "c")).all()
    assert arr(it, "d") == pytest.approx([1, 2, 3])


def test_movmean_columns_of_matrix(it):
    """Down each column: [1 10;2 20;3 30] with k = 2 → [1 10;1.5 15;2.5 25]."""
    run(it, "m = movmean([1 10;2 20;3 30], 2);")
    assert arr(it, "m") == pytest.approx(np.array([[1, 10], [1.5, 15],
                                                   [2.5, 25]]))


def test_smoothdata_with_window_and_refusals(it):
    """smoothdata's movmean is movmean (NaN omitted by default)."""
    run(it, "a = smoothdata([1 2 3 4 5], 'movmean', 3); "
            "b = smoothdata([1 NaN 3], 'movmean', 3);")
    assert arr(it, "a") == pytest.approx([1.5, 2, 3, 4, 4.5])
    assert arr(it, "b") == pytest.approx([1, 2, 3])
    assert "window" in error_of(it, "smoothdata([1 2 3])")
    assert "gaussian" in error_of(it, "smoothdata([1 2 3], 'gaussian', 2)")


def test_detrend_linear_constant_and_quadratic(it):
    """
    [1 3 2 5]': least-squares line through t = 1..4 has slope 5.5/5 = 1.1 and
    passes through (2.5, 2.75); residuals −0.1 0.8 −1.3 0.6. A quadratic
    leaves nothing of t².
    """
    run(it, "a = detrend([1 3 2 5]'); b = detrend([1 3 2 5], 0); "
            "c = detrend((1:5).^2, 2);")
    assert arr(it, "a").ravel() == pytest.approx([-0.1, 0.8, -1.3, 0.6])
    assert arr(it, "a").shape == (4, 1)
    assert arr(it, "b") == pytest.approx([-1.75, 0.25, -0.75, 2.25])
    assert arr(it, "c") == pytest.approx(np.zeros(5), abs=1e-10)
    assert "breakpoints" in error_of(it, "detrend([1 2 3 4], 1, 2)")


# ──────────────────────────────────────────────────────────────
#  Normal distribution, ttest, regress
# ──────────────────────────────────────────────────────────────

def test_normal_pdf_cdf_inverse(it):
    """Closed forms: φ(x) = e^{−x²/2}/√(2π), Φ(x) = (1 + erf(x/√2))/2."""
    run(it, "a = normpdf(0); b = normpdf(1, 1, 2); c = normcdf([0 1.96]); "
            "d = norminv(normcdf(0.3)); e = normcdf(1, 0, 1, 'upper'); "
            "f = normcdf(0, [0 1], 1);")

    def phi(x):
        return (1 + math.erf(x / math.sqrt(2))) / 2
    assert val(it, "a") == pytest.approx(1 / math.sqrt(2 * math.pi))
    assert val(it, "b") == pytest.approx(1 / (2 * math.sqrt(2 * math.pi)))
    assert arr(it, "c") == pytest.approx([0.5, phi(1.96)])
    assert val(it, "d") == pytest.approx(0.3)
    assert val(it, "e") == pytest.approx(1 - phi(1))
    assert arr(it, "f") == pytest.approx([0.5, phi(-1)])


def test_ttest_one_sample_paired_and_options(it):
    """
    [1 2 3] − 0: mean 2, sd 1, t = 2√3, df 2. With 2 df the t CDF is
    ½ + t/(2√(2+t²)), so two-tailed p = 1 − t/√(2+t²) = 1 − √(12/14).
    """
    run(it, "[h, p, ci, st] = ttest([1 2 3]); "
            "[h2, p2] = ttest([2 3 4], [1 1 1]); "
            "h3 = ttest([1 2 3], 0, 'Alpha', 0.1); "
            "[~, p4] = ttest([1 2 3], 0, 'Tail', 'right');")
    t = 2 * math.sqrt(3)
    p = 1 - t / math.sqrt(2 + t * t)
    assert val(it, "h") == 0
    assert val(it, "p") == pytest.approx(p)
    assert val(it, "p2") == pytest.approx(p)
    assert val(it, "h3") == 1
    assert val(it, "p4") == pytest.approx(p / 2)
    st = val(it, "st")
    assert st.tstat == pytest.approx(t)
    assert st.df == 2 and st.sd == pytest.approx(1)
    ci = arr(it, "ci")
    assert ci.shape == (2,)                           # row data: a row
    assert (ci[0] + ci[1]) / 2 == pytest.approx(2)


def test_ttest_ci_with_known_quantile(it):
    """
    [1 2 3 4 5] against 2: mean 3, se = √2.5/√5 = 1/√2. With 4 df the 97.5%
    point of t is 2.7764451; the interval is around the mean of x.
    """
    run(it, "[~, ~, ci] = ttest((1:5)', 2);")
    ci = arr(it, "ci")
    assert ci.shape == (2, 1)
    assert ci.ravel() == pytest.approx([3 - 2.7764451 / math.sqrt(2),
                                        3 + 2.7764451 / math.sqrt(2)],
                                       rel=1e-7)
    assert "TAIL" in error_of(it, "ttest([1 2 3], 0, 'Tail', 'up')")


def test_regress_coefficients_residuals_stats(it):
    """
    y = [1 3 4 7]' on x = 1..4: slope Σdxdy/Σdx² = 9.5/5 = 1.9, intercept
    3.75 − 1.9·2.5 = −1; residuals 0.1 0.2 −0.7 0.4, SSE 0.7, SST 18.75, so
    R² = 1 − 0.7/18.75 and F = (18.75 − 0.7)/(0.7/2).
    """
    run(it, "X = [ones(4,1) (1:4)']; y = [1 3 4 7]'; "
            "[b, bint, r, rint, stats] = regress(y, X);")
    assert arr(it, "b").shape == (2, 1)
    assert arr(it, "b").ravel() == pytest.approx([-1, 1.9])
    assert arr(it, "r").ravel() == pytest.approx([0.1, 0.2, -0.7, 0.4])
    s = arr(it, "stats")
    assert s[0] == pytest.approx(1 - 0.7 / 18.75)
    assert s[1] == pytest.approx(18.05 / 0.35)
    assert s[3] == pytest.approx(0.35)
    bint = arr(it, "bint")
    assert bint.shape == (2, 2)
    assert bint.mean(axis=1) == pytest.approx([-1, 1.9])
    assert arr(it, "rint").shape == (4, 2)


# ──────────────────────────────────────────────────────────────
#  Factorisations
# ──────────────────────────────────────────────────────────────

def test_svd_values_and_factor_shapes(it):
    """diag(3, 4) has singular values 4, 3 (a column, largest first)."""
    run(it, "s = svd([3 0;0 4]); A = [1 2;3 4;5 6]; [U, S, V] = svd(A); "
            "[Ue, Se, Ve] = svd(A, 'econ'); [U0, S0, V0] = svd(A, 0);")
    assert arr(it, "s").shape == (2, 1)
    assert arr(it, "s").ravel() == pytest.approx([4, 3])
    A = np.array([[1, 2], [3, 4], [5, 6]], float)
    U, S, V = arr(it, "U"), arr(it, "S"), arr(it, "V")
    assert U.shape == (3, 3) and S.shape == (3, 2) and V.shape == (2, 2)
    assert U @ S @ V.T == pytest.approx(A)
    Ue, Se, Ve = arr(it, "Ue"), arr(it, "Se"), arr(it, "Ve")
    assert Ue.shape == (3, 2) and Se.shape == (2, 2)
    assert Ue @ Se @ Ve.T == pytest.approx(A)
    assert arr(it, "U0").shape == (3, 2)


def test_qr_forms(it):
    """Q orthogonal, R upper triangular, A*P = Q*R with |diag R| falling."""
    run(it, "A = [1 2;3 4;5 7]; [Q, R] = qr(A); [Qe, Re] = qr(A, 0); "
            "[Q3, R3, P] = qr(A); [~, ~, p] = qr(A, 0);")
    A = np.array([[1, 2], [3, 4], [5, 7]], float)
    Q, R = arr(it, "Q"), arr(it, "R")
    assert Q.shape == (3, 3) and R.shape == (3, 2)
    assert Q @ R == pytest.approx(A)
    assert Q.T @ Q == pytest.approx(np.eye(3))
    assert np.tril(R, -1) == pytest.approx(np.zeros((3, 2)))
    assert arr(it, "Qe").shape == (3, 2) and arr(it, "Re").shape == (2, 2)
    Q3, R3, P = arr(it, "Q3"), arr(it, "R3"), arr(it, "P")
    assert A @ P == pytest.approx(Q3 @ R3)
    assert abs(R3[0, 0]) >= abs(R3[1, 1])
    assert sorted(arr(it, "p").ravel()) == [1, 2]


def test_lu_permuted_l_and_three_outputs(it):
    """
    [1 2;3 4] pivots on 3: P = [0 1;1 0], L = [1 0;1/3 1], U = [3 4;0 2/3].
    With two outputs L comes back as P'L = [1/3 1;1 0].
    """
    run(it, "[L, U] = lu([1 2;3 4]); [L3, U3, P] = lu([1 2;3 4]);")
    assert arr(it, "L") == pytest.approx(np.array([[1 / 3, 1], [1, 0]]))
    assert arr(it, "U") == pytest.approx(np.array([[3, 4], [0, 2 / 3]]))
    assert arr(it, "L3") == pytest.approx(np.array([[1, 0], [1 / 3, 1]]))
    assert arr(it, "P") == pytest.approx(np.array([[0, 1], [1, 0]]))


def test_chol_factor_and_failure(it):
    """
    [4 2;2 3] = R'R with R = [2 1;0 √2]. [1 2;2 1] fails at column 2
    (1 − 4 < 0), so [R, p] gives p = 2 and the 1×1 factor of A(1,1), 1.
    """
    run(it, "R = chol([4 2;2 3]); [R2, p] = chol([1 2;2 1]); "
            "[R3, q] = chol([4 2;2 3]); L = chol([4 2;2 3], 'lower');")
    assert arr(it, "R") == pytest.approx(np.array([[2, 1], [0, math.sqrt(2)]]))
    assert val(it, "p") == 2 and val(it, "R2") == pytest.approx(1)
    assert val(it, "q") == 0
    assert arr(it, "L") == pytest.approx(np.array([[2, 0], [1, math.sqrt(2)]]))
    assert error_of(it, "chol([1 2;2 1])").endswith(
        "Matrix must be positive definite.")


def test_pinv_null_orth(it):
    """
    [1 2;2 4] = vv' with v = [1;2]: its pseudo-inverse is A/‖v‖⁴ = A/25.
    null([1 1]) is ±[1;−1]/√2, orth([1 1;1 1]) ±[1;1]/√2.
    """
    run(it, "P = pinv([1 2;2 4]); N = null([1 1]); O = orth([1 1;1 1]); "
            "Z = null(eye(2));")
    assert arr(it, "P") == pytest.approx(np.array([[1, 2], [2, 4]]) / 25)
    N = arr(it, "N")
    assert N.shape == (2, 1)
    assert np.abs(N.ravel()) == pytest.approx([1 / math.sqrt(2)] * 2)
    assert N[0, 0] == pytest.approx(-N[1, 0])
    Q = arr(it, "O")
    assert Q[0, 0] == pytest.approx(Q[1, 0])
    assert float(Q.T @ Q) == pytest.approx(1)
    assert arr(it, "Z").shape == (2, 0)


def test_matrix_functions(it):
    """
    [0 1;0 0] is nilpotent, so expm = I + A = [1 1;0 1] and logm undoes it.
    sqrt of [1 1;0 1] is [1 ½;0 1] (square it to check).
    """
    run(it, "E = expm([0 1;0 0]); L = logm([1 1;0 1]); S = sqrtm([1 1;0 1]);")
    assert arr(it, "E") == pytest.approx(np.array([[1, 1], [0, 1]]))
    assert arr(it, "L") == pytest.approx(np.array([[0, 1], [0, 0]]), abs=1e-12)
    assert arr(it, "S") == pytest.approx(np.array([[1, 0.5], [0, 1]]))
    assert "square" in error_of(it, "expm([1 2 3])")


def test_cond_norms(it):
    """
    cond(diag(1,2)) = 2. For [1 2;3 4], ‖A‖₁ = 6 and A⁻¹ = [−2 1;1.5 −0.5]
    has ‖·‖₁ = 3.5: cond(A, 1) = 21. A singular matrix is Inf.
    """
    run(it, "a = cond([1 0;0 2]); b = cond([1 2;3 4], 1); "
            "c = cond([1 1;1 1]);")
    assert val(it, "a") == pytest.approx(2)
    assert val(it, "b") == pytest.approx(21)
    assert val(it, "c") == math.inf


# ──────────────────────────────────────────────────────────────
#  cross, dot, triu/tril, circshift, sub2ind/ind2sub
# ──────────────────────────────────────────────────────────────

def test_cross_keeps_orientation(it):
    """x × y = z, as a row for rows and a column for columns."""
    run(it, "a = cross([1 0 0], [0 1 0]); b = cross([0;1;0], [0;0;1]); "
            "m = cross([1 0;0 1;0 0], [0 0;1 0;0 1]);")
    assert arr(it, "a").shape == (3,)
    assert arr(it, "a") == pytest.approx([0, 0, 1])
    assert arr(it, "b").shape == (3, 1)
    assert arr(it, "b").ravel() == pytest.approx([1, 0, 0])
    assert arr(it, "m") == pytest.approx(np.array([[0, 1], [0, 0], [1, 0]]))
    assert "length 3" in error_of(it, "cross([1 2], [3 4])")


def test_dot_vectors_matrices_complex(it):
    """1·4 + 2·5 + 3·6 = 32 across orientations; columns of [1 2;3 4] give
    1+9 and 4+16; dot conjugates the first: conj(i)·i = 1."""
    run(it, "a = dot([1 2 3], [4;5;6]); b = dot([1 2;3 4], [1 2;3 4]); "
            "c = dot(1i, 1i);")
    assert val(it, "a") == pytest.approx(32)
    assert arr(it, "b") == pytest.approx([10, 20])
    assert val(it, "c") == pytest.approx(1)
    assert "same size" in error_of(it, "dot([1 2], [1 2 3])")


def test_triu_tril_offsets(it):
    run(it, "A = [1 2 3;4 5 6;7 8 9]; U = triu(A, 1); L = tril(A, -1); "
            "T = triu(A);")
    assert arr(it, "U") == pytest.approx(np.array([[0, 2, 3], [0, 0, 6],
                                                   [0, 0, 0]]))
    assert arr(it, "L") == pytest.approx(np.array([[0, 0, 0], [4, 0, 0],
                                                   [7, 8, 0]]))
    assert arr(it, "T")[2] == pytest.approx([0, 0, 9])


def test_circshift_forms(it):
    """A vector shifts along its own length; a matrix down its rows."""
    run(it, "a = circshift([1 2 3 4], 1); b = circshift([1;2;3], -1); "
            "A = [1 2;3 4;5 6]; c = circshift(A, 1); d = circshift(A, 1, 2); "
            "e = circshift(A, [1 1]);")
    assert arr(it, "a") == pytest.approx([4, 1, 2, 3])
    assert arr(it, "b").ravel() == pytest.approx([2, 3, 1])
    assert arr(it, "b").shape == (3, 1)
    assert arr(it, "c") == pytest.approx(np.array([[5, 6], [1, 2], [3, 4]]))
    assert arr(it, "d") == pytest.approx(np.array([[2, 1], [4, 3], [6, 5]]))
    assert arr(it, "e") == pytest.approx(np.array([[6, 5], [2, 1], [4, 3]]))


def test_sub2ind_and_ind2sub(it):
    """Column-major: (2,3) of a 2×3 is element 2 + (3−1)·2 = 6."""
    run(it, "k = sub2ind([2 3], 2, 3); ks = sub2ind([2 3], [1 2], [1 3]); "
            "[r, c] = ind2sub([2 3], 6); [rs, cs] = ind2sub([2 3], [1 4]); "
            "one = ind2sub([2 3], 5);")
    assert val(it, "k") == 6
    assert arr(it, "ks") == pytest.approx([1, 6])
    assert (val(it, "r"), val(it, "c")) == (2, 3)
    assert arr(it, "rs") == pytest.approx([1, 2])
    assert arr(it, "cs") == pytest.approx([1, 2])
    assert val(it, "one") == 5
    assert "Out of range" in error_of(it, "sub2ind([2 3], 3, 1)")
    assert "out of range" in error_of(it, "[r,c] = ind2sub([2 3], 7);")


# ──────────────────────────────────────────────────────────────
#  Random integers, permutations, rng
# ──────────────────────────────────────────────────────────────

def test_randi_shapes_and_range(it):
    run(it, "a = randi(6); b = randi(6, 3); c = randi([5 7], 2, 4); "
            "d = randi(10, [1 5]);")
    assert 1 <= val(it, "a") <= 6 and float(val(it, "a")).is_integer()
    assert arr(it, "b").shape == (3, 3)
    c = arr(it, "c")
    assert c.shape == (2, 4) and c.min() >= 5 and c.max() <= 7
    assert np.all(c == np.round(c))
    assert arr(it, "d").shape == (5,)
    assert "IMAX" in error_of(it, "randi(0)")


def test_randperm(it):
    run(it, "p = randperm(6); q = randperm(10, 3);")
    assert sorted(arr(it, "p")) == [1, 2, 3, 4, 5, 6]
    q = arr(it, "q")
    assert q.shape == (3,) and len(set(q)) == 3 and q.max() <= 10
    assert "less than or equal to N" in error_of(it, "randperm(3, 4)")


def test_rng_reproduces_rand_randn_randi(it):
    """Seeding twice gives the same stream for every generator function."""
    run(it, "rng(1); a = rand(1,3); b = randn; c = randi(100); "
            "rng(1); a2 = rand(1,3); b2 = randn; c2 = randi(100); "
            "rng('default'); d = rand; rng(0); d2 = rand;")
    assert arr(it, "a") == pytest.approx(arr(it, "a2"))
    assert val(it, "b") == val(it, "b2") and val(it, "c") == val(it, "c2")
    assert val(it, "d") == val(it, "d2")


def test_rng_settings_round_trip(it):
    """s = rng captures the state; rng(s) puts it back."""
    run(it, "rng(5); randn; s = rng; x = randn(1,2); rng(s); y = randn(1,2);")
    assert arr(it, "x") == pytest.approx(arr(it, "y"))
    s = val(it, "s")
    assert s.Type == "twister" and s.Seed == 5
    assert "nonnegative integer" in error_of(it, "rng(-1)")
    assert "twister" in error_of(it, "rng(1, 'philox')")
