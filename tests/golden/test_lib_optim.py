"""
Fitting, optimisation and integration (``lib_optim``).

Each test types the command as a user would and checks it against a value
worked out by hand, from a closed form, or by an independent route (normal
equations, KKT conditions, an antiderivative, MATLAB's own published
formula re-coded here) — never against what Evans printed.
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
    return results


def error_of(it, source: str) -> str:
    """Run MATLAB that must fail; return the error text."""
    results = it.run_script(source, "matlab")
    failed = [r for r in results if r.error]
    assert failed, f"{source!r} ran without an error"
    return str(failed[0].error)


def val(it, name):
    return it.namespace[name]


def arr(it, name):
    return np.asarray(val(it, name), float)


QUIET = "o = optimoptions('fmincon', 'Display', 'off');"

# ──────────────────────────────────────────────────────────────
#  Least squares and equations
# ──────────────────────────────────────────────────────────────


def test_lsqcurvefit_recovers_exact_exponential(it):
    """Data made from 2*exp(0.5*x): the least-squares optimum is (2, 0.5)
    with zero residual. x comes back shaped like x0 (a row)."""
    run(it, "xd = 0:4; yd = 2*exp(0.5*xd);"
            "[x, rn, res, ef] = lsqcurvefit(@(p,x) p(1)*exp(p(2)*x), "
            "[1 1], xd, yd);")
    assert val(it, "x").shape == (2,)
    assert arr(it, "x") == pytest.approx([2, 0.5], abs=1e-8)
    assert val(it, "rn") == pytest.approx(0, abs=1e-14)
    assert np.shape(val(it, "res")) == (5,)
    assert val(it, "ef") > 0


def test_lsqcurvefit_linear_model_matches_normal_equations(it):
    """A model linear in p: the answer is (A'A)\\A'y, worked here."""
    xd = np.array([0, 1, 2, 3, 4.0])
    yd = np.array([1.1, 2.9, 5.2, 7.1, 8.8])
    A = np.column_stack([xd, np.ones_like(xd)])
    expect = np.linalg.solve(A.T @ A, A.T @ yd)
    run(it, "xd = [0 1 2 3 4]; yd = [1.1 2.9 5.2 7.1 8.8];"
            "[p, rn] = lsqcurvefit(@(p,x) p(1)*x + p(2), [0;0], xd, yd);")
    assert val(it, "p").shape == (2, 1)
    assert arr(it, "p").ravel() == pytest.approx(expect, abs=1e-8)
    assert val(it, "rn") == pytest.approx(
        float(np.sum((A @ expect - yd) ** 2)), rel=1e-8)


def test_lsqcurvefit_bounds_are_honoured(it):
    """Fitting y = p*x to y = 3x with p <= 2: the optimum is on the bound."""
    run(it, "p = lsqcurvefit(@(p,x) p*x, 0, 1:3, 3*(1:3), [], 2);")
    assert val(it, "p") == pytest.approx(2, abs=1e-9)


def test_lsqnonlin_overdetermined_linear(it):
    """Residuals p1-1, p2-2, p1+p2-4: normal equations give (4/3, 7/3)."""
    run(it, "[x, rn, r, ef] = lsqnonlin(@(p) [p(1)-1; p(2)-2; "
            "p(1)+p(2)-4], [0; 0]);")
    assert arr(it, "x").ravel() == pytest.approx([4 / 3, 7 / 3], abs=1e-9)
    # each residual is 1/3 in size
    assert val(it, "rn") == pytest.approx(3 * (1 / 3) ** 2, rel=1e-9)
    assert arr(it, "r").shape == (3, 1)


def test_fsolve_solves_a_square_system(it):
    """x² + y² = 2, x = y has the root (1, 1) nearest (2, 0.5)."""
    run(it, "[x, fv, ef] = fsolve(@(x) [x(1)^2+x(2)^2-2; x(1)-x(2)], "
            "[2 0.5]);")
    assert arr(it, "x") == pytest.approx([1, 1], abs=1e-9)
    assert val(it, "ef") == 1
    assert arr(it, "fv").shape == (2, 1)


def test_fsolve_reports_no_solution(it):
    """x² + 1 = 0 has no real root: exitflag -2, never a claimed root."""
    run(it, "[x, fv, ef] = fsolve(@(x) x^2 + 1, 3);")
    assert val(it, "ef") == -2
    assert val(it, "fv") >= 1 - 1e-9


def test_fsolve_prints_matlab_message(it):
    """MATLAB's default Display 'final' prints 'Equation solved.'"""
    results = run(it, "x = fsolve(@(x) x - 2, 0);")
    text = "".join(r.output or "" for r in results)
    assert "Equation solved." in text
    results = run(it, "x = fsolve(@(x) x - 2, 0, "
                      "optimoptions('fsolve', 'Display', 'off'));")
    assert "Equation solved." not in "".join(r.output or "" for r in results)

# ──────────────────────────────────────────────────────────────
#  Minimisation
# ──────────────────────────────────────────────────────────────


def test_fminunc_quadratic(it):
    """(x1-1)² + 3(x2+2)² has its minimum 0 at (1, -2); the gradient there
    is zero and the Hessian diag(2, 6)."""
    run(it, "[x, fv, ef, out, g, H] = fminunc(@(x) (x(1)-1)^2 + "
            "3*(x(2)+2)^2, [0 0]);")
    assert arr(it, "x") == pytest.approx([1, -2], abs=1e-6)
    assert val(it, "fv") == pytest.approx(0, abs=1e-10)
    assert val(it, "ef") == 1
    assert arr(it, "g").shape == (2, 1)
    assert arr(it, "H") == pytest.approx(np.diag([2, 6]), abs=1e-4)


def test_fminunc_rosenbrock(it):
    """Rosenbrock's minimum is (1, 1)."""
    run(it, "x = fminunc(@(x) 100*(x(2)-x(1)^2)^2 + (1-x(1))^2, [-1.2 1]);")
    assert arr(it, "x") == pytest.approx([1, 1], abs=1e-4)


def test_fmincon_linear_inequality(it):
    """min x1²+x2² s.t. x1+x2 >= 2 (written -x1-x2 <= -2): by symmetry and
    the KKT condition 2x = λ(1,1), the answer is (1, 1), f = 2."""
    run(it, QUIET + "[x, fv, ef] = fmincon(@(x) x(1)^2+x(2)^2, [3 3], "
            "[-1 -1], -2, [], [], [], [], [], o);")
    assert arr(it, "x") == pytest.approx([1, 1], abs=1e-7)
    assert val(it, "fv") == pytest.approx(2, abs=1e-7)
    assert val(it, "ef") == 1


def test_fmincon_equality_and_bounds(it):
    """min (x1-3)² + (x2-3)² with x1 + x2 = 2 and x1 <= 0.5: the equality
    alone gives (1, 1); the bound moves it to (0.5, 1.5)."""
    run(it, QUIET + "x = fmincon(@(x) (x(1)-3)^2+(x(2)-3)^2, [0; 0], [], "
            "[], [1 1], 2, [-Inf; -Inf], [0.5; Inf], [], o);")
    assert val(it, "x").shape == (2, 1)
    assert arr(it, "x").ravel() == pytest.approx([0.5, 1.5], abs=1e-7)


def test_fmincon_nonlinear_constraint(it):
    """min x1 + x2 on the unit disc: (-1/√2, -1/√2), f = -√2."""
    run(it, QUIET + """
[x, fv, ef] = fmincon(@(x) x(1)+x(2), [0.5 0.5], [], [], [], [], [], [], @disc, o);
function [c, ceq] = disc(x)
  c = x(1)^2 + x(2)^2 - 1;
  ceq = [];
end
""")
    r = -1 / math.sqrt(2)
    assert arr(it, "x") == pytest.approx([r, r], abs=1e-6)
    assert val(it, "fv") == pytest.approx(-math.sqrt(2), abs=1e-7)


def test_fmincon_refuses_one_output_nonlcon(it):
    """An anonymous nonlcon gives one output; MATLAB requires [c, ceq]."""
    msg = error_of(it, QUIET + "x = fmincon(@(x) x^2, 1, [], [], [], [], "
                   "[], [], @(x) x - 2, o);")
    assert "two" in msg and "ceq" in msg


def test_fmincon_infeasible(it):
    """x >= 2 and x <= 1 cannot both hold: exitflag -2."""
    run(it, QUIET + "[x, fv, ef] = fmincon(@(x) x^2, 0, [1; -1], [1; -2], "
            "[], [], [], [], [], o);")
    assert val(it, "ef") == -2


def test_optimoptions_refuses_unknown_and_callbacks(it):
    assert "not an option" in error_of(it, "o = optimoptions('fmincon', "
                                           "'Bogus', 1);")
    assert "OutputFcn" in error_of(it, "o = optimoptions('fminunc', "
                                       "'OutputFcn', @(x) 0);"
                                       "x = fminunc(@(x) x^2, 1, o);")

# ──────────────────────────────────────────────────────────────
#  LP, MILP, QP
# ──────────────────────────────────────────────────────────────


def test_linprog_vertex_by_hand(it):
    """max x1 + 2x2 s.t. x1+x2 <= 4, x1 <= 3, x >= 0: the vertices are
    (0,0), (3,0), (3,1), (0,4); the best is (0,4) with value 8. The
    multiplier on x1+x2 <= 4 is 2 (the objective gains 2 per unit of b)."""
    run(it, "[x, fv, ef, out, lam] = linprog([-1 -2], [1 1; 1 0], [4; 3], "
            "[], [], [0 0]);")
    assert val(it, "x").shape == (2, 1)
    assert arr(it, "x").ravel() == pytest.approx([0, 4], abs=1e-9)
    assert val(it, "fv") == pytest.approx(-8)
    assert val(it, "ef") == 1
    lam = val(it, "lam")
    assert np.asarray(lam.ineqlin, float).ravel() == pytest.approx([2, 0])
    # reduced cost of x1 at its lower bound: -1 + 2 = 1
    assert np.asarray(lam.lower, float).ravel() == pytest.approx([1, 0])


def test_linprog_default_bounds_are_free(it):
    """MATLAB's lb defaults to -Inf (scipy's to 0): min x s.t. x >= -5,
    written -x <= 5, is -5."""
    run(it, "x = linprog(1, -1, 5);")
    assert val(it, "x") == pytest.approx(-5)


def test_linprog_infeasible_and_unbounded(it):
    run(it, "[x, fv, ef] = linprog(1, [1; -1], [1; -2]);")
    assert val(it, "ef") == -2 and np.size(val(it, "x")) == 0
    run(it, "[x, fv, ef] = linprog(-1, [], [], [], [], 0);")
    assert val(it, "ef") == -3


def test_intlinprog_by_enumeration(it):
    """max x1 + x2 with 2x1 + x2 <= 4.5, x1 + 2x2 <= 4.5, x >= 0, integer:
    enumerating the integer points gives the best value 2 (the LP gives 3)."""
    run(it, "[x, fv, ef] = intlinprog([-1 -1], [1 2], [2 1; 1 2], "
            "[4.5; 4.5], [], [], [0 0], []);")
    best = min(-(a + b) for a in range(5) for b in range(5)
               if 2 * a + b <= 4.5 and a + 2 * b <= 4.5)
    assert val(it, "fv") == pytest.approx(best)
    x = arr(it, "x").ravel()
    assert np.all(x == np.round(x)) and -(x.sum()) == best


def test_intlinprog_mixed(it):
    """max 3x1 + 2x2 with x1 + x2 <= 3.5, x1 <= 2.2, x1 integer, x2 free
    continuous >= 0: x1 = 2, x2 = 1.5, value 9."""
    run(it, "[x, fv] = intlinprog([-3 -2], 1, [1 1; 1 0], [3.5; 2.2], [], "
            "[], [0 0], []);")
    assert arr(it, "x").ravel() == pytest.approx([2, 1.5])
    assert val(it, "fv") == pytest.approx(-9)


def test_quadprog_kkt_active_constraint(it):
    """min x1² + x2² - 2x1 - 5x2 s.t. x1 + 2x2 <= 3. The unconstrained
    minimum (1, 2.5) violates it, so it is active: 2x - (2,5) + λ(1,2) = 0
    and x1 + 2x2 = 3 give λ = 6/5, x = (0.4, 1.3)."""
    run(it, "[x, fv, ef, out, lam] = quadprog([2 0; 0 2], [-2; -5], [1 2], "
            "3);")
    assert arr(it, "x").ravel() == pytest.approx([0.4, 1.3], abs=1e-10)
    assert val(it, "fv") == pytest.approx(0.16 + 1.69 - 0.8 - 6.5)
    assert np.asarray(val(it, "lam").ineqlin, float).ravel() == \
        pytest.approx([1.2], abs=1e-8)


def test_quadprog_equality_only_closed_form(it):
    """min ½x'Hx + f'x, Aeq x = beq solves the KKT system directly."""
    H = np.array([[4.0, 1], [1, 3]])
    f = np.array([1.0, -2])
    Aeq = np.array([[1.0, 1]])
    K = np.block([[H, Aeq.T], [Aeq, np.zeros((1, 1))]])
    expect = np.linalg.solve(K, np.concatenate([-f, [1.0]]))[:2]
    run(it, "x = quadprog([4 1; 1 3], [1 -2], [], [], [1 1], 1);")
    assert arr(it, "x").ravel() == pytest.approx(expect, abs=1e-12)


def test_quadprog_bounds(it):
    """min (x-3)² = ½·2x² - 6x + 9 with 0 <= x <= 1: x = 1."""
    run(it, "x = quadprog(2, -6, [], [], [], [], 0, 1);")
    assert val(it, "x") == pytest.approx(1, abs=1e-10)


def test_quadprog_nonconvex_and_unbounded(it):
    run(it, "[x, fv, ef] = quadprog([1 0; 0 -1], [0 0]);")
    assert val(it, "ef") == -6
    run(it, "[x, fv, ef] = quadprog([1 0; 0 0], [0 -1], [], [], [], [], "
            "[-1 -Inf], [1 Inf]);")
    assert val(it, "ef") == -3

# ──────────────────────────────────────────────────────────────
#  Quadrature
# ──────────────────────────────────────────────────────────────


def test_integral_polynomial_and_infinite(it):
    """∫₀¹ x² = 1/3; ∫ e^{-x²} over the line = √π; ∫₀^∞ e^{-x} = 1."""
    run(it, "a = integral(@(x) x.^2, 0, 1);"
            "b = integral(@(x) exp(-x.^2), -Inf, Inf);"
            "c = integral(@(x) exp(-x), 0, Inf);"
            "d = integral(@(x) exp(x), -Inf, 0);")
    assert val(it, "a") == pytest.approx(1 / 3, rel=1e-12)
    assert val(it, "b") == pytest.approx(math.sqrt(math.pi), rel=1e-9)
    assert val(it, "c") == pytest.approx(1, rel=1e-9)
    assert val(it, "d") == pytest.approx(1, rel=1e-9)


def test_integral_endpoint_singularity_and_reversed(it):
    """∫₀¹ 1/√x = 2; ∫₁⁰ x = -1/2."""
    run(it, "a = integral(@(x) 1./sqrt(x), 0, 1); b = integral(@(x) x, 1, 0);")
    assert val(it, "a") == pytest.approx(2, rel=1e-8)
    assert val(it, "b") == pytest.approx(-0.5, rel=1e-12)


def test_integral_tolerances_and_waypoints(it):
    """∫₀² |x-1| = 1 (a kink at the waypoint 1); RelTol 1e-12 on ∫₀^π sin
    = 2 is met."""
    run(it, "a = integral(@(x) abs(x-1), 0, 2, 'Waypoints', 1);"
            "b = integral(@(x) sin(x), 0, pi, 'RelTol', 1e-12, "
            "'AbsTol', 1e-14);")
    assert val(it, "a") == pytest.approx(1, rel=1e-13)
    assert val(it, "b") == pytest.approx(2, rel=1e-12)


def test_integral_array_valued(it):
    """∫₀¹ [x, x², x³] = [1/2, 1/3, 1/4]."""
    run(it, "q = integral(@(x) [x, x^2, x^3], 0, 1, 'ArrayValued', true);")
    assert arr(it, "q") == pytest.approx([1 / 2, 1 / 3, 1 / 4], rel=1e-10)


def test_integral_needs_vectorised_fun(it):
    """@(x) 5 returns one value for many points: MATLAB's error."""
    msg = error_of(it, "q = integral(@(x) 5, 0, 1);")
    assert "same size as the input" in msg
    assert "complex" in error_of(it, "q = integral(@(x) x, 0, 1i);")


def test_quadgk_log_with_error_bound(it):
    """∫₀¹ ln x = -1; errbnd is small and positive."""
    run(it, "[q, e] = quadgk(@(x) log(x), 0, 1);")
    assert val(it, "q") == pytest.approx(-1, rel=1e-6)
    assert 0 <= val(it, "e") < 1e-5


def test_integral2_rectangle_and_variable_limit(it):
    """∫₀¹∫₀² xy dy dx = 1; over the triangle 0 <= y <= x <= 1, ∫∫ xy = 1/8;
    ∫₀¹∫_{x²}^{x} 1 = 1/2 - 1/3."""
    run(it, "a = integral2(@(x,y) x.*y, 0, 1, 0, 2);"
            "b = integral2(@(x,y) x.*y, 0, 1, 0, @(x) x);"
            "c = integral2(@(x,y) ones(size(x)), 0, 1, @(x) x.^2, @(x) x);")
    assert val(it, "a") == pytest.approx(1, rel=1e-9)
    assert val(it, "b") == pytest.approx(1 / 8, rel=1e-9)
    assert val(it, "c") == pytest.approx(1 / 6, rel=1e-9)

# ──────────────────────────────────────────────────────────────
#  Polynomials, splines, 2-D interpolation
# ──────────────────────────────────────────────────────────────


def test_polyder_forms(it):
    """d/dx (x³+2x²+3x+4) = 3x²+4x+3; d/dx[(x+1)(x-1)] = 2x;
    d/dx[x/(x+1)] = 1/(x+1)²."""
    run(it, "p = polyder([1 2 3 4]); r = polyder([1 1], [1 -1]);"
            "[q, d] = polyder([1 0], [1 1]); c = polyder(7);")
    assert arr(it, "p") == pytest.approx([3, 4, 3])
    assert arr(it, "r") == pytest.approx([2, 0])
    assert val(it, "q") == 1
    assert arr(it, "d") == pytest.approx([1, 2, 1])
    assert val(it, "c") == 0


def test_polyint(it):
    """∫(3x²+2x+1) = x³+x²+x+k."""
    run(it, "p = polyint([3 2 1]); q = polyint([3 2 1], 5);")
    assert arr(it, "p") == pytest.approx([1, 1, 1, 0])
    assert arr(it, "q") == pytest.approx([1, 1, 1, 5])


def test_spline_reproduces_cubic_not_a_knot(it):
    """A not-a-knot spline through samples of a cubic is that cubic."""
    run(it, "s = spline(0:4, (0:4).^3 - 2*(0:4), [0.5 2.5 5]);"
            "pp = spline(0:4, (0:4).^3 - 2*(0:4)); v = ppval(pp, [0.5 2.5 5]);")
    q = np.array([0.5, 2.5, 5])
    assert arr(it, "s") == pytest.approx(q ** 3 - 2 * q, abs=1e-12)
    assert arr(it, "v") == pytest.approx(q ** 3 - 2 * q, abs=1e-12)
    assert val(it, "pp").form == "pp" and val(it, "pp").pieces == 4


def test_spline_three_points_is_a_parabola_and_clamped(it):
    """Three points: MATLAB's spline is the interpolating parabola.
    Clamped (two extra values): the end slopes of x² on [0,2] are 0 and 4,
    so the spline is x² itself."""
    run(it, "a = spline([0 1 3], [1 2 10], 2);"
            "b = spline(0:2, [0 0 1 4 4], 1.5);")
    coeffs = np.polyfit([0, 1, 3], [1, 2, 10], 2)
    assert val(it, "a") == pytest.approx(np.polyval(coeffs, 2), abs=1e-12)
    assert val(it, "b") == pytest.approx(2.25, abs=1e-12)


def _matlab_pchip(x, y, xq):
    """MATLAB's pchip.m (pchipslopes + Hermite), re-coded by hand."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    h = np.diff(x)
    dl = np.diff(y) / h
    n = x.size
    d = np.zeros(n)
    for k in range(n - 2):
        if np.sign(dl[k]) * np.sign(dl[k + 1]) > 0:
            hs = h[k] + h[k + 1]
            w1 = (h[k] + hs) / (3 * hs)
            w2 = (hs + h[k + 1]) / (3 * hs)
            dmax = max(abs(dl[k]), abs(dl[k + 1]))
            dmin = min(abs(dl[k]), abs(dl[k + 1]))
            d[k + 1] = dmin / (w1 * (dl[k] / dmax) + w2 * (dl[k + 1] / dmax))

    def end(h0, h1, d0, d1):
        s = ((2 * h0 + h1) * d0 - h0 * d1) / (h0 + h1)
        if np.sign(s) != np.sign(d0):
            return 0.0
        if np.sign(d0) != np.sign(d1) and abs(s) > abs(3 * d0):
            return 3 * d0
        return s
    d[0] = end(h[0], h[1], dl[0], dl[1])
    d[-1] = end(h[-1], h[-2], dl[-1], dl[-2])
    out = []
    for q in xq:
        k = min(max(np.searchsorted(x, q, side="right") - 1, 0), n - 2)
        s = q - x[k]
        c = (3 * dl[k] - 2 * d[k] - d[k + 1]) / h[k]
        b = (d[k] - 2 * dl[k] + d[k + 1]) / h[k] ** 2
        out.append(y[k] + s * (d[k] + s * (c + s * b)))
    return np.array(out)


def test_pchip_matches_matlab_formula(it):
    """Uneven spacing, a sign change and a flat stretch: compared with
    MATLAB's pchip.m slope rules coded independently above."""
    x = [0, 1, 2.5, 3, 5, 6]
    y = [0, 2, 1, 1, 4, 3]
    xq = np.linspace(-0.5, 6.5, 29)
    run(it, "x = [0 1 2.5 3 5 6]; y = [0 2 1 1 4 3];"
            "v = pchip(x, y, linspace(-0.5, 6.5, 29));")
    assert arr(it, "v") == pytest.approx(_matlab_pchip(x, y, xq), abs=1e-12)


def test_interp2_linear_spline_and_outside(it):
    """V = x + 10y is reproduced exactly by bilinear and spline
    interpolation; outside the grid is NaN; a row and a column of queries
    make a grid, as MATLAB's interp2 does."""
    run(it, "[X, Y] = meshgrid(1:4, 1:3); V = X + 10*Y;"
            "a = interp2(X, Y, V, 2.5, 1.5);"
            "b = interp2(X, Y, V, 3.2, 2.7, 'spline');"
            "c = interp2(X, Y, V, 5, 1);"
            "G = interp2(V, [1.5 2.5], [1; 2; 3]);"
            "W = X.^2 .* Y.^3; s = interp2(X, Y, W, 2.5, 1.5, 'spline');"
            "n = interp2(X, Y, V, 2.4, 1.2, 'nearest');")
    assert val(it, "a") == pytest.approx(17.5)
    assert val(it, "b") == pytest.approx(30.2)
    assert math.isnan(val(it, "c"))
    G = arr(it, "G")
    assert G.shape == (3, 2)
    assert G == pytest.approx(np.array([1.5, 2.5])[None, :]
                              + 10 * np.array([1, 2, 3.0])[:, None])
    # x² and y³ are reproduced by a not-a-knot spline along each axis
    assert val(it, "s") == pytest.approx(2.5 ** 2 * 1.5 ** 3, abs=1e-10)
    assert val(it, "n") == pytest.approx(2 + 10)


def test_interp2_refuses_cubic(it):
    assert "cubic" in error_of(it, "[X,Y] = meshgrid(1:4); "
                                   "z = interp2(X, Y, X+Y, 2, 2, 'cubic');")


def test_griddata_linear_on_a_triangle_and_hull(it):
    """On the single triangle (0,0),(1,0),(0,1), linear interpolation of
    v = 1 + 2x + 3y is exact; outside the hull it is NaN."""
    run(it, "g = griddata([0 1 0], [0 0 1], [1 3 4], [0.2 0.9], [0.3 0.9]);"
            "h = griddata([0 1 0], [0 0 1], [1 3 4], 0.1, 0.1, 'nearest');")
    g = arr(it, "g")
    assert g[0] == pytest.approx(1 + 0.4 + 0.9)
    assert math.isnan(g[1])
    assert val(it, "h") == 1
    assert "v4" in error_of(it, "g = griddata([0 1 0], [0 0 1], [1 2 3], "
                                ".1, .1, 'v4');")

# ──────────────────────────────────────────────────────────────
#  Curve fitting
# ──────────────────────────────────────────────────────────────


def test_fit_poly2_matches_normal_equations_and_gof(it):
    """poly2 on noisy data: coefficients from the normal equations; gof from
    its definitions; 95% bounds from (J'J)^-1·s² and t(0.975, dfe)."""
    from scipy import stats
    x = np.arange(1.0, 9)
    y = np.array([2.2, 4.1, 8.3, 13.9, 22.4, 30.8, 43.0, 55.9])
    B = np.vander(x, 3)
    p = np.linalg.solve(B.T @ B, B.T @ y)
    sse = float(np.sum((B @ p - y) ** 2))
    sst = float(np.sum((y - y.mean()) ** 2))
    dfe = 5
    half = stats.t.ppf(0.975, dfe) * np.sqrt(
        np.diag(np.linalg.inv(B.T @ B)) * sse / dfe)
    run(it, "x = (1:8)'; y = [2.2 4.1 8.3 13.9 22.4 30.8 43.0 55.9]';"
            "[f, gof] = fit(x, y, 'poly2'); c = coeffvalues(f);"
            "ci = confint(f); p1 = f.p1; yq = f([2; 3]);")
    assert arr(it, "c") == pytest.approx(p, rel=1e-10)
    assert val(it, "p1") == pytest.approx(p[0], rel=1e-10)
    gof = val(it, "gof")
    assert gof.sse == pytest.approx(sse, rel=1e-9)
    assert gof.rsquare == pytest.approx(1 - sse / sst, rel=1e-12)
    assert gof.dfe == dfe
    assert gof.adjrsquare == pytest.approx(1 - (sse / dfe) / (sst / 7))
    assert gof.rmse == pytest.approx(math.sqrt(sse / dfe))
    assert arr(it, "ci") == pytest.approx(np.vstack([p - half, p + half]),
                                          rel=1e-8)
    assert arr(it, "yq").shape == (2, 1)
    assert arr(it, "yq").ravel() == pytest.approx(np.polyval(p, [2, 3]))


def test_fit_exp1_recovers_exact_data(it):
    """Data exactly 3·e^{-0.4x}: a = 3, b = -0.4."""
    run(it, "x = (0:0.5:5)'; [f, gof] = fit(x, 3*exp(-0.4*x), 'exp1');"
            "a = f.a; b = f.b;")
    assert val(it, "a") == pytest.approx(3, rel=1e-9)
    assert val(it, "b") == pytest.approx(-0.4, rel=1e-9)
    assert val(it, "gof").sse == pytest.approx(0, abs=1e-18)


@pytest.mark.parametrize("model, expr, coeffs", [
    ("power1", "2*x.^1.7", [2, 1.7]),
    ("power2", "3*x.^-0.5 + 1", [3, -0.5, 1]),
    ("sin1", "1.5*sin(2.2*x + 0.4)", [1.5, 2.2, 0.4]),
    ("gauss1", "4*exp(-((x-1.2)/0.5).^2)", [4, 1.2, 0.5]),
])
def test_fit_nonlinear_library_models_on_exact_data(it, model, expr, coeffs):
    """On exact data the least-squares optimum is the generating model."""
    run(it, f"x = (0.1:0.1:3)'; f = fit(x, {expr}, '{model}');"
            "c = coeffvalues(f);")
    assert arr(it, "c") == pytest.approx(coeffs, abs=1e-7)


def test_fit_exp2_on_exact_data(it):
    """The two exponential terms come back in either order."""
    run(it, "x = (0.1:0.1:3)'; f = fit(x, 2*exp(0.3*x) + "
            "0.5*exp(-1.5*x), 'exp2'); c = coeffvalues(f);")
    c = arr(it, "c")
    pairs = sorted([(c[1], c[0]), (c[3], c[2])])
    assert pairs[0] == pytest.approx((-1.5, 0.5), abs=1e-6)
    assert pairs[1] == pytest.approx((0.3, 2), abs=1e-6)


def test_fit_display_and_names(it):
    results = run(it, "f = fit((1:5)', [3 5 7 9 11.5]', 'poly1')")
    text = "".join(r.output or "" for r in results)
    assert "Linear model Poly1:" in text
    assert "f(x) = p1*x + p2" in text
    assert "Coefficients (with 95% confidence bounds):" in text
    run(it, "n = coeffnames(f);")
    assert list(val(it, "n")) == ["p1", "p2"]


def test_fit_weights_and_exclude(it):
    """Exclude the outlier: the line through the rest is exact (y = 2x+1).
    Weights w: the weighted normal equations."""
    run(it, "x = (1:5)'; y = [3 5 7 9 50]';"
            "f = fit(x, y, 'poly1', 'Exclude', x == 5); c = coeffvalues(f);"
            "g = fit(x, y, 'poly1', 'Weights', [1 2 1 2 1]); d = coeffvalues(g);")
    assert arr(it, "c") == pytest.approx([2, 1], abs=1e-12)
    x = np.arange(1.0, 6)
    y = np.array([3, 5, 7, 9, 50.0])
    W = np.diag([1, 2, 1, 2, 1.0])
    B = np.vander(x, 2)
    assert arr(it, "d") == pytest.approx(
        np.linalg.solve(B.T @ W @ B, B.T @ W @ y), rel=1e-10)


def test_fit_refusals(it):
    assert "custom" in error_of(it, "f = fit((1:5)', (1:5)', 'a*x^2+b');")
    assert "nonpositive" in error_of(it, "f = fit((0:4)', (1:5)', 'power1');")
    assert "robust" in error_of(it, "f = fit((1:5)', (1:5)', 'poly1', "
                                    "'Robust', 'LAR');").lower()
