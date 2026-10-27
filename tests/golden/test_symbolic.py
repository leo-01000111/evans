"""
Symbolic maths: ``syms``, the Laplace transform both ways, and the algebra a
control course does by hand — partial fractions, ``(sI − A)⁻¹``, solving for
a gain.

Expected values are the textbook's (a transform table, a hand inversion), and
expected *text* is MATLAB's own display, since how a formula prints is most
of what a student sees of it.
"""

from __future__ import annotations

import numpy as np
import pytest
import sympy as sp

from evans.console import Interpreter, set_figure_sink
from evans.console.figures import recording_sink
from evans.console.matlab_runtime import Struct
from evans.console.symbolic import Sym, _exact


@pytest.fixture
def sink():
    recorder = recording_sink()
    previous = set_figure_sink(recorder)
    yield recorder
    set_figure_sink(previous)


@pytest.fixture
def it(sink):
    return Interpreter()


def run(it, source: str) -> str:
    results = it.run_script(source, "matlab")
    failed = [r for r in results if r.error]
    assert not failed, f"{failed[0].source!r} → {failed[0].error}"
    return "\n".join(r.display() for r in results)


def fails(it, source: str) -> str:
    results = it.run_script(source, "matlab")
    assert results[-1].error, "expected an error"
    return results[-1].error


def text(it, name: str) -> str:
    value = it.namespace[name]
    assert isinstance(value, Sym), f"{name} is a {type(value).__name__}"
    return str(value)


def same(it, name: str, expected: str) -> None:
    """``name`` equals the formula ``expected``, whatever form it prints in."""
    value = it.namespace[name].expr
    names = {"heaviside": sp.Heaviside, "dirac": sp.DiracDelta,
             **{str(s): s for s in value.free_symbols}}
    want = sp.sympify(expected.replace("^", "**"), locals=names)
    assert sp.simplify(value - want) == 0, f"{name} = {value}, not {want}"


# ──────────────────────────────────────────────────────────────
#  Making symbols
# ──────────────────────────────────────────────────────────────

def test_syms_makes_symbols_in_the_workspace(it):
    run(it, "syms s t")
    assert text(it, "s") == "s" and text(it, "t") == "t"
    assert run(it, "class(s)").endswith("'sym'")


def test_syms_replaces_the_console_s(it):
    # The console starts with s = tf('s'); after syms s, s is a symbol and
    # formulas built from it stay symbolic.
    run(it, "syms s\nG = 1/(s^2 + 2*s + 1);")
    assert text(it, "G") == "1/(s^2 + 2*s + 1)"


def test_syms_takes_assumptions(it):
    run(it, "syms a positive\nsyms x real")
    assert it.namespace["a"].expr.is_positive
    assert it.namespace["x"].expr.is_real


def test_syms_alone_lists_the_symbols(it):
    out = run(it, "syms b a\nsyms")
    assert out.splitlines()[-1].split() == ["a", "b"]


def test_symbolic_functions_are_refused_by_name(it):
    assert "not supported" in fails(it, "syms y(t)")


def test_sym_of_a_double_is_exact(it):
    run(it, "a = sym(0.1); b = sym(1/3); c = sym(pi); d = sym(sqrt(2));")
    assert [text(it, n) for n in "abcd"] == ["1/10", "1/3", "pi", "sqrt(2)"]


def test_a_double_meeting_a_symbol_is_made_exact():
    assert _exact(0.25) == sp.Rational(1, 4)
    assert _exact(2 * np.pi / 3) == 2 * sp.pi / 3
    assert _exact(0.123456789) == sp.Rational(123456789, 1000000000)
    assert _exact(float("inf")) == sp.oo


def test_sym_array_names_its_elements(it):
    run(it, "k = sym('k', [1 3]);\nK = sym('K', [2 2]);")
    assert text(it, "k") == "[k1, k2, k3]"
    assert text(it, "K").splitlines()[1] == "[K2_1, K2_2]"


def test_str2sym_reads_matlab_spelling(it):
    run(it, "syms s\nf = str2sym('s^2 + 2*s + heaviside(s)');")
    assert text(it, "f") == "s^2 + 2*s + heaviside(s)"


# ──────────────────────────────────────────────────────────────
#  Display
# ──────────────────────────────────────────────────────────────

def test_a_formula_prints_as_matlab_writes_it(it):
    out = run(it, "syms s\nF = 1/(s^2 + 1)")
    assert "F =\n\n    1/(s^2 + 1)" in out


def test_a_symbolic_matrix_prints_in_rows(it):
    run(it, "syms x\nA = [x 1; 0 x^2];")
    assert text(it, "A") == "[x, 1  ]\n[0, x^2]"


def test_matlab_names_for_special_functions(it):
    run(it, "syms t\nf = heaviside(t - 1) + dirac(t) + abs(t) + exp(1)*1i;")
    assert set(text(it, "f").replace("+", " ").split()) >= {
        "heaviside(t", "dirac(t)", "abs(t)"}
    assert "1i" in text(it, "f")


# ──────────────────────────────────────────────────────────────
#  Laplace
# ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("f, F", [
    ("1", "1/s"),
    ("t", "1/s^2"),
    ("t^2", "2/s^3"),
    ("exp(-3*t)", "1/(s + 3)"),
    ("sin(2*t)", "2/(s^2 + 4)"),
    ("cos(2*t)", "s/(s^2 + 4)"),
    ("exp(-2*t)*sin(3*t)", "3/((s + 2)^2 + 9)"),
    ("t*exp(-t)", "1/(s + 1)^2"),
    ("heaviside(t - 2)", "exp(-2*s)/s"),
    ("dirac(t)", "1"),
    ("dirac(t - 1)", "exp(-s)"),
])
def test_laplace_matches_the_table(it, f, F):
    run(it, f"syms t s\nF = laplace({f});")
    same(it, "F", F)


@pytest.mark.parametrize("F, f", [
    ("1/s", "1"),
    ("1/(s + 1)", "exp(-t)"),
    ("1/(s*(s + 1))", "1 - exp(-t)"),
    ("1/(s^2 + 2*s + 5)", "exp(-t)*sin(2*t)/2"),
    ("(s + 3)/((s + 1)*(s + 2))", "2*exp(-t) - exp(-2*t)"),
    ("exp(-2*s)/s^2", "(t - 2)*heaviside(t - 2)"),
])
def test_ilaplace_inverts_by_hand(it, F, f):
    run(it, f"syms s t\nf = ilaplace({F});")
    same(it, "f", f)


def test_ilaplace_gives_the_answer_for_t_after_zero(it):
    # MATLAB writes 1 - exp(-t), not (1 - exp(-t))*heaviside(t).
    run(it, "syms s\nf = ilaplace(1/(s*(s + 1)));")
    assert "heaviside" not in text(it, "f")


def test_laplace_with_a_symbolic_parameter(it):
    run(it, "syms t s\nsyms a positive\nF = laplace(exp(-a*t));")
    same(it, "F", "1/(a + s)")


def test_laplace_and_ilaplace_variables_can_be_named(it):
    run(it, "syms tau w x\nF = laplace(exp(-tau), tau, w);\n"
            "g = ilaplace(1/(w + 4), w, x);")
    same(it, "F", "1/(w + 1)")
    same(it, "g", "exp(-4*x)")


def test_laplace_defaults_to_z_for_a_function_of_s(it):
    run(it, "syms s\nF = laplace(exp(-s));")
    assert "z" in text(it, "F")


def test_a_step_response_by_hand(it):
    # The worked example of every first course: Y(s) = G(s)/s, invert, and
    # compare with step().
    run(it, "syms s t\nG = 4/(s^2 + 2*s + 4);\ny = ilaplace(G/s);\n"
            "h = matlabFunction(y);\ntt = linspace(0, 5, 30);\n"
            "Gn = tf(4, [1 2 4]);\nyn = step(Gn, tt);")
    numeric = np.ravel(it.namespace["yn"])
    symbolic = it.namespace["h"](it.namespace["tt"])
    np.testing.assert_allclose(symbolic, numeric, atol=1e-6)


# ──────────────────────────────────────────────────────────────
#  Algebra
# ──────────────────────────────────────────────────────────────

def test_simplify_cancels(it):
    run(it, "syms s\nH = simplify((s^2 - 1)/(s + 1));")
    assert text(it, "H") == "s - 1"


def test_expand_factor_collect(it):
    run(it, "syms s k\na = expand((s + 1)^3);\nb = factor(s^2 + 3*s + 2);\n"
            "c = collect(s*k + s^2 + k*s^2, s);")
    assert text(it, "a") == "s^3 + 3*s^2 + 3*s + 1"
    assert text(it, "b") == "(s + 1)*(s + 2)"
    same(it, "c", "(k + 1)*s^2 + k*s")


def test_factor_of_a_number_is_its_primes(it):
    run(it, "p = factor(84);")
    np.testing.assert_array_equal(it.namespace["p"], [2, 2, 3, 7])


def test_partfrac_splits_into_simple_fractions(it):
    run(it, "syms s\nP = partfrac(1/(s*(s + 1)*(s + 2)));")
    same(it, "P", "1/(2*s) - 1/(s + 1) + 1/(2*(s + 2))")
    assert text(it, "P").count("/") == 3


def test_subs_forms(it):
    run(it, "syms s a\nG = a/(s + 1);\n"
            "g1 = subs(G, s, 1i);\n"
            "g2 = subs(G, {s, a}, {0, 5});\n"
            "g3 = subs(G, 3);\n"         # the default variable is s
            "a = 2;\ng4 = subs(G);")    # a from the workspace
    same(it, "g1", "a/(1 + I)")
    same(it, "g2", "5")
    same(it, "g4", "2/(s + 1)")
    assert "s" not in text(it, "g3")


def test_subs_a_vector_gives_a_vector(it):
    run(it, "syms x\nv = subs(x^2, x, [1 2 3]);")
    np.testing.assert_array_equal(it.namespace["v"].shape, (1, 3))
    assert text(it, "v") == "[1, 4, 9]"


def test_double_converts_and_refuses_free_symbols(it):
    run(it, "syms s\nd = double(subs(1/(s + 1), s, 3));\n"
            "M = double([sym(1)/2, sym(pi)]);")
    assert it.namespace["d"] == pytest.approx(0.25)
    np.testing.assert_allclose(it.namespace["M"], [0.5, np.pi])
    assert "symbolic variables" in fails(it, "syms x\ndouble(x + 1)")


def test_numden_and_sym2poly_make_a_tf(it):
    run(it, "syms s\nT = (s + 2)/(s^2 + 3*s + 2) + 1/s;\n"
            "[N, D] = numden(T);\nG = tf(sym2poly(N), sym2poly(D));")
    G = it.namespace["G"]
    # 1/(s + 1) + 1/s once (s + 2) cancels: coprime, as MATLAB's numden.
    np.testing.assert_allclose(np.ravel(G.num[0][0]), [2, 1])
    np.testing.assert_allclose(np.ravel(G.den[0][0]), [1, 1, 0])


def test_sym2poly_refuses_two_variables(it):
    assert "one variable" in fails(it, "syms s k\nsym2poly(s^2 + k)")


def test_poly2sym(it):
    run(it, "syms x\np = poly2sym([1 -2 3], x);")
    assert text(it, "p") == "x^2 - 2*x + 3"


def test_state_space_to_transfer_function_symbolically(it):
    # C (sI - A)⁻¹ B: the derivation students check ss2tf against.
    run(it, "syms s\nA = [0 1; -2 -3]; B = [0; 1]; C = [1 0];\n"
            "Phi = inv(s*eye(2) - A);\nT = simplify(C*Phi*B);\n"
            "p = det(s*eye(2) - A);")
    same(it, "T", "1/(s^2 + 3*s + 2)")
    same(it, "p", "s^2 + 3*s + 2")
    assert it.namespace["Phi"].shape == (2, 2)


def test_matrix_operators_keep_matlab_meanings(it):
    run(it, "syms x\nA = [x 1; 0 x];\nP = A^2;\nE = A.^2;\nT = A.';\n"
            "e = A(1, 2);\nr = A(2, :);")
    assert text(it, "P") == "[x^2, 2*x]\n[0  , x^2]"
    assert text(it, "E") == "[x^2, 1  ]\n[0  , x^2]"
    assert text(it, "T") == "[x, 0]\n[1, x]"
    assert text(it, "e") == "1"
    assert text(it, "r") == "[0, x]"


def test_for_steps_through_columns(it):
    out = run(it, "syms x\nfor v = [x, x^2, x^3]\n  disp(v)\nend")
    assert out.split() == ["x", "x^2", "x^3"]


# ──────────────────────────────────────────────────────────────
#  Calculus and equations
# ──────────────────────────────────────────────────────────────

def test_diff_picks_t_over_a_constant(it):
    # MATLAB's default variable is the one closest to x: t, not a.
    run(it, "syms a t\nd = diff(a*t^3);\nd2 = diff(a*t^3, 2);\n"
            "da = diff(a*t^3, a);")
    same(it, "d", "3*a*t^2")
    same(it, "d2", "6*a*t")
    same(it, "da", "t^3")


def test_int_indefinite_and_definite(it):
    run(it, "syms t x\nF = int(x^2);\nI = int(exp(-t), t, 0, Inf);\n"
            "J = int(x, 0, 2);")
    same(it, "F", "x^3/3")
    same(it, "I", "1")
    same(it, "J", "2")


def test_limit_including_one_sided(it):
    run(it, "syms x\nL = limit(sin(x)/x, x, 0);\n"
            "R = limit(1/x, x, 0, 'right');\nN = limit(1/x, x, 0);\n"
            "F = limit((1 + 1/x)^x, x, Inf);")
    same(it, "L", "1")
    assert text(it, "R") == "Inf"
    assert text(it, "N") == "NaN"
    assert text(it, "F") == "exp(1)"


def test_final_value_theorem(it):
    run(it, "syms s\nG = 5/(s^2 + 3*s + 2);\nyinf = limit(s*G/s, s, 0);")
    same(it, "yinf", "5/2")


def test_taylor(it):
    run(it, "syms x\nT = taylor(exp(x), x, 'Order', 3);")
    same(it, "T", "1 + x + x^2/2")


def test_solve_one_variable_gives_a_column(it):
    run(it, "syms x\nr = solve(x^2 - 4 == 0, x);\nq = solve(x^2 - 9);")
    assert it.namespace["r"].shape == (2, 1)
    assert sorted(int(v) for v in it.namespace["r"].expr) == [-2, 2]
    assert sorted(int(v) for v in it.namespace["q"].expr) == [-3, 3]


def test_solve_several_variables(it):
    run(it, "syms a b\nS = solve(a + b == 3, a - b == 1);\n"
            "[xa, xb] = solve(a + b == 3, a - b == 1, a, b);")
    S = it.namespace["S"]
    assert isinstance(S, Struct) and list(S) == ["a", "b"]
    assert str(S["a"]) == "2" and str(S["b"]) == "1"
    assert text(it, "xa") == "2" and text(it, "xb") == "1"


def test_solve_for_a_gain(it):
    # Where does 1 + K/(s(s+2)) put a double pole? Solve the discriminant.
    run(it, "syms K s\nK0 = solve(4 - 4*K == 0, K);")
    assert text(it, "K0") == "1"


# ──────────────────────────────────────────────────────────────
#  Conditions, conversion and plotting
# ──────────────────────────────────────────────────────────────

def test_if_on_a_formula_needs_proof(it):
    assert "isAlways" in fails(it, "syms x\nif x == 1, disp(1), end")
    out = run(it, "if sym(2) == 2, disp('yes'), end")
    assert out.strip().endswith("yes")


def test_is_always(it):
    run(it, "syms x real\na = isAlways(x^2 >= 0);\nb = isAlways(x > 0);")
    assert it.namespace["a"] is True and it.namespace["b"] is False


def test_vpa_and_latex(it):
    run(it, "v = vpa(sym(pi), 10);\nsyms x\nL = latex(x^2/2);")
    assert text(it, "v") == "3.141592654"
    assert it.namespace["L"] == r"\frac{x^{2}}{2}"


def test_numeric_heaviside_and_dirac(it):
    run(it, "h = heaviside([-1 0 1]);\nd = dirac([0 1]);")
    np.testing.assert_array_equal(it.namespace["h"], [0, 0.5, 1])
    np.testing.assert_array_equal(it.namespace["d"], [np.inf, 0])


def test_matlab_function_evaluates_on_arrays(it):
    run(it, "syms t a\nh = matlabFunction(a*exp(-t));\n"
            "y = h(2, [0 1]);\nk = matlabFunction(sym(3));\nz = k();")
    np.testing.assert_allclose(it.namespace["y"], [2, 2 * np.exp(-1)])
    assert it.namespace["z"] == 3


def test_fplot_draws_a_formula_and_a_handle(it, sink):
    run(it, "syms t\nfplot(exp(-t)*sin(3*t), [0 5])\n"
            "fplot(@(x) x.^2, [0 2])")
    first, second = sink.figures[-2:]
    trace = first.traces[0]
    assert trace.x[0] == 0 and trace.x[-1] == 5
    np.testing.assert_allclose(trace.y, np.exp(-trace.x) * np.sin(3 * trace.x),
                               atol=1e-12)
    np.testing.assert_allclose(second.traces[0].y, second.traces[0].x ** 2)


def test_numbers_are_untouched_by_the_overloads(it):
    # diff, det, inv and exp still mean what they did on numbers.
    run(it, "a = diff([1 4 9]);\nb = det([1 2; 3 4]);\nc = exp(0);\n"
            "d = inv([2 0; 0 4]);")
    np.testing.assert_array_equal(it.namespace["a"], [3, 5])
    assert it.namespace["b"] == pytest.approx(-2)
    assert it.namespace["c"] == 1
    np.testing.assert_allclose(it.namespace["d"], [[0.5, 0], [0, 0.25]])


def test_python_operators_work_on_symbols():
    x = Sym(sp.Symbol("x"))
    assert str((x + 1) ** 2 / 2) == "(x + 1)^2/2"
    assert str(2 * x - np.float64(0.5)) == "2*x - 1/2"
