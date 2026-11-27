"""
Silent wrong answers found while writing the help pages.

Each test types the command the way a user would and checks it against
MATLAB's documented behaviour or a value worked out by hand, never against
what Evans printed before the fix. (The earlier ones are in
``test_confident_liars.py``.)
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


def printed(it, source: str) -> str:
    """Run one MATLAB command; return what it printed."""
    result = it.command(source)
    assert result.ok, f"{source} → {result.error}"
    return result.output or ""


def error_of(it, source: str) -> str:
    """Run MATLAB that must fail; return the error text."""
    results = it.run_script(source, "matlab")
    failed = [r for r in results if r.error]
    assert failed, f"{source!r} ran without an error"
    return str(failed[0].error)


def val(it, name):
    return it.namespace[name]


def num(it, name) -> float:
    return float(np.asarray(val(it, name), dtype=float).reshape(-1)[0])


# ──────────────────────────────────────────────────────────────
#  fzero: exitflag, TolX and output
# ──────────────────────────────────────────────────────────────

def test_fzero_output_has_matlabs_fields(it):
    """
    From ``x0 = 1`` on ``x² − 2`` the search widens by √2 from ``dx = 1/50``
    until ``1 + dx ≥ √2``: ``0.02·√2^k ≥ 0.4142`` first holds at ``k = 9``.
    Each step evaluates both ends, so the search costs 1 + 2·9 = 19 calls,
    and every Brent iteration one more.
    """
    run(it, "[x, fv, flag, out] = fzero(@(x) x^2 - 2, 1);")
    out = val(it, "out")
    assert set(out) == {"intervaliterations", "iterations", "funcCount",
                        "algorithm", "message"}
    assert out["intervaliterations"] == 9
    assert out["funcCount"] == 19 + out["iterations"]
    assert out["iterations"] > 0
    assert out["algorithm"] == "bisection, interpolation"
    assert "Zero found in the interval" in out["message"]
    assert num(it, "flag") == 1
    assert num(it, "x") == pytest.approx(math.sqrt(2), abs=1e-14)


def test_fzero_bracket_counts_its_two_end_calls(it):
    run(it, "[x, fv, flag, out] = fzero(@cos, [1 2]);")
    out = val(it, "out")
    assert out["intervaliterations"] == 0
    assert out["funcCount"] == out["iterations"] + 2
    assert out["message"] == "Zero found in the interval [1, 2]"
    assert num(it, "x") == pytest.approx(math.pi / 2, abs=1e-14)


def test_fzero_honours_tolx(it):
    """A loose ``TolX`` stops sooner, and the answer is still within it."""
    run(it, "f = @(x) x^3 - 2*x - 5;\n"
            "[x1, ~, ~, o1] = fzero(f, [2 3]);\n"
            "[x2, ~, ~, o2] = fzero(f, [2 3], optimset('TolX', 1e-2));")
    root = 2.0945514815423265
    assert num(it, "x1") == pytest.approx(root, abs=1e-14)
    assert abs(num(it, "x2") - root) < 4e-2
    assert num(it, "x2") != pytest.approx(root, abs=1e-12)
    assert val(it, "o2")["funcCount"] < val(it, "o1")["funcCount"]


def test_fzero_singular_point_gives_minus_5(it):
    """``tan`` changes sign across its pole at π/2: MATLAB's exitflag −5."""
    run(it, "[x, fv, flag] = fzero(@tan, [1 2], optimset('Display','off'));")
    assert num(it, "flag") == -5
    assert num(it, "x") == pytest.approx(math.pi / 2, abs=1e-12)
    assert abs(num(it, "fv")) > 1e10


def test_fzero_inf_during_search_gives_minus_3_and_nan(it):
    run(it, "[x, fv, flag, o] = fzero(@(x) x^2 + 1, 1, "
            "optimset('Display','off'));")
    assert num(it, "flag") == -3
    assert math.isnan(num(it, "x")) and math.isnan(num(it, "fv"))
    assert "NaN or Inf" in val(it, "o")["message"]


def test_fzero_complex_during_search_gives_minus_4(it):
    run(it, "[x, fv, flag] = fzero(@(x) sqrt(x) + 1, 1, "
            "optimset('Display','off'));")
    assert num(it, "flag") == -4
    assert math.isnan(num(it, "x"))


def test_fzero_no_sign_change_gives_minus_6(it):
    run(it, "[x, fv, flag] = fzero(@(x) 5, 1, optimset('Display','off'));")
    assert num(it, "flag") == -6
    assert math.isnan(num(it, "x"))


def test_fzero_failure_is_reported_unless_display_off(it):
    shown = printed(it, "x = fzero(@(x) x^2 + 1, 1)")
    assert "Exiting fzero" in shown
    quiet = printed(it, "x = fzero(@(x) x^2 + 1, 1, optimset('Display','off'));")
    assert "Exiting fzero" not in quiet
    assert math.isnan(num(it, "x"))


def test_fzero_zero_at_the_start(it):
    run(it, "[x, fv, flag, o] = fzero(@(x) x - 3, 3);")
    assert num(it, "x") == 3 and num(it, "flag") == 1
    assert val(it, "o")["funcCount"] == 1


def test_fzero_bracket_without_sign_change_still_errors(it):
    assert "differ in sign" in error_of(it, "fzero(@(x) x^2 + 1, [0 1])")


# ──────────────────────────────────────────────────────────────
#  struct2table returns a real table
# ──────────────────────────────────────────────────────────────

def test_struct2table_is_a_table(it):
    run(it, "s = struct('a', {1, 2}); T = struct2table(s);\n"
            "t = istable(T); c = class(T); a = T.a;\n"
            "vn = T.Properties.VariableNames; h = height(T);\n"
            "R = T(1,:); r = height(R); ra = R.a;\n"
            "S = table2struct(T); sa = [S.a]; ss = size(S);\n"
            "C = table2cell(T); A = table2array(T);")
    assert val(it, "t") and val(it, "c") == "table"
    np.testing.assert_array_equal(np.asarray(val(it, "a")).reshape(-1),
                                  [1, 2])
    assert np.asarray(val(it, "a")).shape == (2, 1)
    assert list(val(it, "vn")) == ["a"]
    assert num(it, "h") == 2 and num(it, "r") == 1 and num(it, "ra") == 1
    np.testing.assert_array_equal(np.asarray(val(it, "sa")).reshape(-1),
                                  [1, 2])
    np.testing.assert_array_equal(np.asarray(val(it, "ss")).reshape(-1),
                                  [2, 1])
    assert [float(np.asarray(v)) for v in val(it, "C")] == [1, 2]
    np.testing.assert_array_equal(np.asarray(val(it, "A")).reshape(-1),
                                  [1, 2])
    printed(it, "summary(T)")


def test_struct2table_text_fields_become_cellstr(it):
    run(it, "s = struct('name', {'Ann', 'Bob'}, 'n', {1, 2});\n"
            "T = struct2table(s); nm = T.name; n = T.n; w = width(T);")
    assert list(val(it, "nm")) == ["Ann", "Bob"]
    np.testing.assert_array_equal(np.asarray(val(it, "n")).reshape(-1),
                                  [1, 2])
    assert num(it, "w") == 2


def test_struct2table_scalar_struct_of_columns(it):
    """A scalar struct whose fields have m rows is an m-row table."""
    run(it, "s.x = [1; 2; 3]; s.y = [4; 5; 6]; T = struct2table(s);\n"
            "sz = size(T); y = T.y;")
    np.testing.assert_array_equal(np.asarray(val(it, "sz")).reshape(-1),
                                  [3, 2])
    np.testing.assert_array_equal(np.asarray(val(it, "y")).reshape(-1),
                                  [4, 5, 6])


def test_struct2table_mixed_sizes_go_into_a_cell(it):
    run(it, "s = struct('v', {[1 2], 7}); T = struct2table(s); v = T.v;")
    v = val(it, "v")
    np.testing.assert_array_equal(np.asarray(v[0]).reshape(-1), [1, 2])
    assert float(np.asarray(v[1])) == 7


def test_struct2table_asarray(it):
    assert "same number of rows" in error_of(
        it, "s.x = [1; 2; 3]; s.y = 7; T = struct2table(s);")
    run(it, "s.x = [1; 2; 3]; s.y = 7;\n"
            "T = struct2table(s, 'AsArray', true); sz = size(T);\n"
            "x = T.x; y = T.y;")
    np.testing.assert_array_equal(np.asarray(val(it, "sz")).reshape(-1),
                                  [1, 2])
    np.testing.assert_array_equal(np.asarray(val(it, "x")[0]).reshape(-1),
                                  [1, 2, 3])
    assert num(it, "y") == 7


def test_struct2table_rownames(it):
    run(it, "T = struct2table(struct('a', {1, 2}), 'RowNames', {'r1', 'r2'});"
            "\nb = T('r2', :).a; rn = T.Properties.RowNames;")
    assert num(it, "b") == 2
    assert list(val(it, "rn")) == ["r1", "r2"]


def test_struct2table_wrong_input_is_a_matlab_error(it):
    assert "struct" in error_of(it, "struct2table(5)")
    assert "struct" in error_of(it, "struct2table({1})")
