"""
Commands that showed a Python error instead of a MATLAB one.

Found while writing the help pages (``docs/HISTORY.md``, part 4, Phase 4):
a traceback, a numpy message or a Python exception name where MATLAB gives
its own words, or a crash where MATLAB returns an answer. Each test types the
command the way a user would and checks MATLAB's documented message or a
value worked out by hand.
"""

from __future__ import annotations

import os

import numpy as np
import pytest
from scipy import signal

from evans.console import Interpreter, set_figure_sink
from evans.console.figures import recording_sink


@pytest.fixture
def it():
    previous = set_figure_sink(recording_sink())
    yield Interpreter()
    set_figure_sink(previous)


def run(it, source: str) -> str:
    """Run MATLAB, insist it succeeded; return what it printed."""
    results = it.run_script(source, "matlab")
    failed = [r for r in results if r.error]
    assert not failed, f"{failed[0].source!r} → {failed[0].error}"
    return "".join(r.output or "" for r in results)


def error_of(it, source: str) -> str:
    """Run MATLAB that must fail; return the error text."""
    results = it.run_script(source, "matlab")
    failed = [r for r in results if r.error]
    assert failed, f"{source!r} ran without an error"
    return str(failed[0].error)


def val(it, name):
    return it.namespace[name]


NOT_ENOUGH = "Not enough input arguments."
TOO_MANY = "Too many input arguments."


# ──────────────────────────────────────────────────────────────
#  Filter design: the four-output state-space form
# ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("design, args, scipy_args", [
    ("butter", "2,0.2", (2, 0.2)),
    ("cheby1", "2,1,0.2", (2, 1, 0.2)),
    ("ellip", "2,1,40,0.2", (2, 1, 40, 0.2)),
    ("butter", "2,[0.2 0.4]", (2, [0.2, 0.4], "bandpass")),
])
def test_iir_design_returns_state_space(it, design, args, scipy_args):
    """
    ``[A,B,C,D] = butter(...)`` is a realisation of the same filter: its
    transfer function ``C(zI-A)^-1 B + D`` has the ``[b,a]`` coefficients.
    """
    run(it, f"[A,B,C,D] = {design}({args});")
    b, a = getattr(signal, design)(*scipy_args)
    A, B, C, D = (np.atleast_2d(np.asarray(val(it, n), float))
                  for n in "ABCD")
    order = len(a) - 1
    assert A.shape == (order, order)
    num, den = signal.ss2tf(A, B.reshape(order, 1), C.reshape(1, order),
                            D.reshape(1, 1))
    assert den == pytest.approx(a, abs=1e-10)
    assert num.ravel() == pytest.approx(b, abs=1e-10)


# ──────────────────────────────────────────────────────────────
#  save: a value it cannot write is not a missing variable
# ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("value, cls", [
    ("@sin", "function_handle"),
    ("table([1;2])", "table"),
])
def test_save_names_the_class_it_cannot_write(it, tmp_path, value, cls):
    path = (tmp_path / "t.mat").as_posix()
    message = error_of(it, f"f = {value}; save('{path}', 'f')")
    assert "not found" not in message
    assert f"class '{cls}'" in message and "'f'" in message


def test_save_of_a_missing_variable_still_says_not_found(it, tmp_path):
    path = (tmp_path / "t.mat").as_posix()
    assert "Variable 'nope' not found." in error_of(
        it, f"save('{path}', 'nope')")


def test_save_writes_a_string_as_text(it, tmp_path):
    path = (tmp_path / "t.mat").as_posix()
    run(it, f"""f = "abc"; save('{path}', 'f'); clear f; load('{path}');""")
    assert val(it, "f") == "abc"


# ──────────────────────────────────────────────────────────────
#  Missing and extra arguments
# ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("source", [
    "fft()", "freqz()", "findpeaks()", "butter(2)",
    "f = @(t,y) -y; ode45(f, [0 1])", "f = @(x) x - 1; fzero(f)",
    "f = @(x) x^2; fminsearch(f)", "gt(1)", "ceil()", "log10()",
])
def test_missing_arguments_say_not_enough(it, source):
    assert NOT_ENOUGH in error_of(it, source)


@pytest.mark.parametrize("source", [
    "log10(1, 2)", "ceil(1, 2)", "cd('a', 'b')", "pwd(1)",
])
def test_extra_arguments_say_too_many(it, source):
    assert TOO_MANY in error_of(it, source)


def test_an_error_inside_a_function_is_not_relabelled(it):
    """Only a refused call becomes "Not enough input arguments."."""
    message = error_of(it, "f = @(x) x(3); f([1 2])")
    assert NOT_ENOUGH not in message


# ──────────────────────────────────────────────────────────────
#  Signal processing: bad values
# ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("source", ["fft('a')", "fft({1})"])
def test_fft_of_text_or_a_cell_is_refused(it, source):
    assert "Invalid data type" in error_of(it, source)


def test_filter_with_initial_conditions_of_the_wrong_length(it):
    message = error_of(it, "filter(1, [1 -0.5], [1 2 3], [1 2])")
    assert message.endswith("Initial conditions must be a vector of "
                            "length max(length(a),length(b))-1.")


def test_filter_with_initial_conditions_still_works(it):
    """``y(n) = x(n) + 0.5 y(n-1)`` with ``zi = 0.5``: 1.5, 2.75, 4.375."""
    run(it, "[y, zf] = filter(1, [1 -0.5], [1 2 3], 0.5);")
    assert np.ravel(val(it, "y")) == pytest.approx([1.5, 2.75, 4.375])
    assert float(np.ravel(val(it, "zf"))[0]) == pytest.approx(2.1875)


# ──────────────────────────────────────────────────────────────
#  cd and addpath
# ──────────────────────────────────────────────────────────────

def test_cd_dotdot_and_dot_as_commands(it, tmp_path):
    sub = tmp_path / "sub"
    sub.mkdir()
    top = tmp_path.as_posix()
    run(it, f"cd('{top}'); cd sub; a = pwd; cd .; b = pwd; cd ..; c = pwd;")
    assert os.path.samefile(val(it, "a"), sub)
    assert os.path.samefile(val(it, "b"), sub)
    assert os.path.samefile(val(it, "c"), tmp_path)


def test_operators_after_a_name_are_not_commands(it):
    run(it, "x = [1 2]; y = x .* 2; z = x.';")
    assert np.ravel(val(it, "y")) == pytest.approx([2, 4])
    assert np.shape(val(it, "z")) == (2, 1)


def test_addpath_warns_about_a_missing_folder(it, tmp_path):
    missing = (tmp_path / "no_such_folder").as_posix()
    out = run(it, f"addpath('{missing}')")
    assert "Warning: Name is nonexistent or not a directory" in out
    assert not any("no_such_folder" in p for p in it._matlab.path)


@pytest.mark.parametrize("source", ["addpath({'lib'})", "addpath(5)"])
def test_addpath_refuses_what_is_not_text(it, source):
    assert "Arguments must contain a character vector." in error_of(
        it, source)


def test_addpath_adds_a_folder_that_exists(it, tmp_path):
    run(it, f"addpath('{tmp_path.as_posix()}')")
    assert any(os.path.samefile(p, tmp_path) for p in it._matlab.path
               if os.path.isdir(p))


# ──────────────────────────────────────────────────────────────
#  all / any: 'all' and the dimension argument
# ──────────────────────────────────────────────────────────────

def test_all_and_any_over_all_elements(it):
    run(it, "a = all([1 1; 0 1], 'all'); b = any([0 0; 0 1], 'all'); "
            "c = all([1 1; 1 1], 'all');")
    assert val(it, "a") is False or val(it, "a") == 0
    assert val(it, "b") == 1 and val(it, "c") == 1


@pytest.mark.parametrize("dim", ["'a'", "1.5", "0", "-1"])
def test_all_refuses_a_bad_dimension(it, dim):
    assert "Dimension argument must be a positive integer scalar" in \
        error_of(it, f"all([1 1], {dim})")


# ──────────────────────────────────────────────────────────────
#  Elementwise maths: text, cells, complex, single
# ──────────────────────────────────────────────────────────────

def test_ceil_of_char_is_of_its_codes(it):
    run(it, "a = ceil('a'); b = floor('ab'); c = abs('a');")
    assert val(it, "a") == 97
    assert np.ravel(val(it, "b")) == pytest.approx([97, 98])
    assert val(it, "c") == 97


def test_ceil_of_complex_rounds_each_part(it):
    run(it, "a = ceil(1.5 + 2.5i); b = floor(-1.5 + 2.5i); c = fix(-1.5 - 2.5i);")
    assert complex(val(it, "a")) == 2 + 3j
    assert complex(val(it, "b")) == -2 + 2j
    assert complex(val(it, "c")) == -1 - 2j


@pytest.mark.parametrize("source, name, cls", [
    ('ceil("a")', "ceil", "string"),
    ("ceil({1})", "ceil", "cell"),
    ("log10({1})", "log10", "cell"),
    ("log10('a')", "log10", "char"),
    ('log10("a")', "log10", "string"),
    ("log2('a')", "log2", "char"),
])
def test_elementwise_maths_refuses_types_as_matlab_does(it, source, name,
                                                         cls):
    assert (f"Undefined function '{name}' for input arguments of type "
            f"'{cls}'.") in error_of(it, source)


@pytest.mark.parametrize("fn", ["log10", "log2", "sqrt", "exp", "sin"])
def test_floating_maths_keeps_single(it, fn):
    run(it, f"c = class({fn}(single(100)));")
    assert val(it, "c") == "single"


def test_log10_of_single_has_the_right_value(it):
    run(it, "y = log10(single(100)); d = class(log10(100));")
    assert float(val(it, "y")) == pytest.approx(2.0)
    assert val(it, "d") == "double"


# ──────────────────────────────────────────────────────────────
#  Relational operators
# ──────────────────────────────────────────────────────────────

def test_gt_of_complex_compares_real_parts(it):
    """MATLAB orders complex numbers by their real parts only."""
    run(it, "a = gt(2+3i, 1); b = gt(1+3i, 1+2i); c = (1+2i) == (1+2i);")
    assert val(it, "a") == 1
    assert val(it, "b") == 0
    assert val(it, "c") == 1


@pytest.mark.parametrize("source", ["gt([1 2 3], [1 2])",
                                    "gt(ones(2,3), ones(3,2))"])
def test_gt_of_mismatched_sizes(it, source):
    assert "Arrays have incompatible sizes for this operation." in \
        error_of(it, source)


@pytest.mark.parametrize("source", ["gt({1}, {2})", "gt('b', {'a'})"])
def test_gt_of_a_cell_is_refused(it, source):
    assert "Operator '>' is not supported for operands of type 'cell'." in \
        error_of(it, source)


def test_gt_of_a_number_and_char_compares_codes(it):
    run(it, "a = gt(1, 'a'); b = 'a' > 96;")
    assert val(it, "a") == 0
    assert val(it, "b") == 1


# ──────────────────────────────────────────────────────────────
#  clear in the same script
# ──────────────────────────────────────────────────────────────

def test_a_variable_cleared_in_the_same_script_is_gone(it):
    assert "Unrecognized function or variable 'x'." in error_of(
        it, "x = 1; clear x; x")


def test_a_cleared_name_finds_the_function_again(it):
    run(it, "pi = 3; clear pi; p = pi; nan = 5; clear nan; n = nan;")
    assert val(it, "p") == pytest.approx(np.pi)
    assert np.isnan(val(it, "n"))


@pytest.mark.parametrize("source", [
    "x = 1; y = 2; clear; y",
    "x = 1; clear('x'); x",
    "x = 1; clear x*; x",
    "s.a = 1; clear s; s.a",
])
def test_every_form_of_clear_in_a_script(it, source):
    assert "Unrecognized function or variable" in error_of(it, source)


def test_a_cleared_variable_can_be_assigned_again(it):
    run(it, "x = 1; y = 2; clear x; x = 4; x = x + y;")
    assert val(it, "x") == 6
