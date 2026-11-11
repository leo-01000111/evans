"""
Writing into numeric arrays: in place when nobody else holds the array.

``a(k) = v`` used to copy the whole array, so filling a pre-allocated vector
in a loop was quadratic. The runtime now writes in place an array that only
the variable being written holds (see ``matlab_runtime._OWNED``). That is the
"confident liar" risk of ``docs/PLAN.md``: if anything else could see the
array, it would change behind its back. So every way a second reference to an
array can appear has its own test here, each checked against MATLAB's value
semantics.

Most cases write to the array once first ("warm-up"): that write copies the
array and makes the copy the variable's own, so the later writes are the ones
done in place.
"""

from __future__ import annotations

import time

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
    results = it.run_script(source, "matlab")
    failed = [r for r in results if r.error]
    assert not failed, f"{failed[0].source!r} → {failed[0].error}"


def val(it, name):
    return it.namespace[name]


def same(x, expected):
    return np.array_equal(np.asarray(x).ravel(), np.asarray(expected).ravel())


def folder(tmp_path, **files: str) -> str:
    for name, text in files.items():
        (tmp_path / f"{name}.m").write_text(text)
    return str(tmp_path).replace("\\", "/")


# A vector the variable owns: written once, so the next writes are in place.
OWN = "a = zeros(1,4); a(1) = 1; "


# ──────────────────────────────────────────────────────────────
#  Another variable, a container, a view
# ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("source, expected", [
    pytest.param(OWN + "b = a; b(2) = 9; r = a(2);", 0, id="b=a, write b"),
    pytest.param(OWN + "b = a; a(2) = 9; r = b(2);", 0, id="b=a, write a"),
    pytest.param(OWN + "b = a; a(2) = 9; b(3) = 7; r = a(3) + 10*b(2);", 0,
                 id="b=a, write both"),
    pytest.param(OWN + "c = {a}; a(2) = 9; r = c{1}(2);", 0,
                 id="cell literal, write a"),
    pytest.param(OWN + "c = {a}; c{1}(2) = 9; r = a(2);", 0,
                 id="cell literal, write cell"),
    pytest.param(OWN + "c = {}; c{1} = a; a(2) = 9; r = c{1}(2);", 0,
                 id="cell element, write a"),
    pytest.param("c = {zeros(1,4)}; c{1}(1) = 1; a = c{1}; c{1}(2) = 9; "
                 "r = a(2);", 0, id="taken out of a cell, write cell"),
    pytest.param("c = {zeros(1,4)}; c{1}(1) = 1; d = c; c{1}(2) = 9; "
                 "r = d{1}(2);", 0, id="cell copied, write its array"),
    pytest.param(OWN + "s.f = a; a(2) = 9; r = s.f(2);", 0,
                 id="struct field, write a"),
    pytest.param(OWN + "s.f = a; s.f(2) = 9; r = a(2);", 0,
                 id="struct field, write field"),
    pytest.param(OWN + "s.g.f = a; a(2) = 9; r = s.g.f(2);", 0,
                 id="nested struct field"),
    pytest.param("s.f = zeros(1,4); s.f(1) = 1; t = s; s.f(2) = 9; "
                 "r = t.f(2);", 0, id="struct copied, write its array"),
    pytest.param("s.f = zeros(1,4); s.f(1) = 1; t = s; t.f(2) = 9; "
                 "r = s.f(2);", 0, id="struct copied, write the copy"),
    pytest.param(OWN + "s = struct('f', {1, 2}); s(2).f = a; a(2) = 9; "
                 "r = s(2).f(2);", 0, id="struct array element"),
    pytest.param(OWN + "b = a(:); a(2) = 9; r = b(2);", 0, id="view a(:)"),
    pytest.param(OWN + "b = a(:); b(3) = 9; r = a(3);", 0,
                 id="view a(:), write the view"),
    pytest.param(OWN + "b = a(2:3); a(2) = 9; r = b(1);", 0,
                 id="slice a(2:3)"),
    pytest.param(OWN + "b = a'; a(2) = 9; r = b(2);", 0, id="transpose"),
    pytest.param(OWN + "b = a.'; a(2) = 9; r = b(2);", 0,
                 id="plain transpose"),
    pytest.param(OWN + "b = reshape(a, 2, 2); a(2) = 9; r = b(2);", 0,
                 id="reshape"),
    pytest.param(OWN + "b = a(:)'; a(2) = 9; r = b(2);", 0,
                 id="view of a view"),
    pytest.param(OWN + "b = double(a); a(2) = 9; r = b(2);", 0,
                 id="double() of a double"),
    pytest.param(OWN + "b = real(a); a(2) = 9; r = b(2);", 0, id="real()"),
    pytest.param(OWN + "b = squeeze(a); a(2) = 9; r = b(2);", 0,
                 id="squeeze()"),
    pytest.param(OWN + "b = +a; a(2) = 9; r = b(2);", 0, id="unary plus"),
    pytest.param(OWN + "[p, q] = deal(a); p(2) = 9; r = q(2) + a(2);", 0,
                 id="deal"),
    pytest.param(OWN + "eval('b = a;'); a(2) = 9; r = b(2);", 0, id="eval"),
    pytest.param(OWN + "n = num2cell(a); a(1) = 9; r = n{1};", 1,
                 id="num2cell"),
])
def test_a_write_never_reaches_another_holder(it, source, expected):
    run(it, source)
    assert val(it, "r") == expected


def test_a_view_written_in_the_same_statement(it):
    """``a(2:5) = a(1:4)``: the right side overlaps the left."""
    run(it, "a = 1:5; a(1) = 1; a(2:5) = a(1:4); "
            "b = 1:5; b(1) = 1; b(1:4) = b(2:5); "
            "c = 1:5; c(1) = 1; c(:) = c(end:-1:1);")
    assert same(val(it, "a"), [1, 1, 2, 3, 4])
    assert same(val(it, "b"), [2, 3, 4, 5, 5])
    assert same(val(it, "c"), [5, 4, 3, 2, 1])


def test_a_matrix_column_view(it):
    run(it, "A = zeros(3); A(1) = 1; B = A(:, 2); A(2, 2) = 9; r = B(2); "
            "C = A(2, :); A(2, 3) = 7; q = C(3);")
    assert (val(it, "r"), val(it, "q")) == (0, 0)


def test_python_aliases_are_respected(it):
    """``b = a`` typed as Python shares the ndarray; a MATLAB write to ``a``
    afterwards must not reach ``b``."""
    run(it, OWN)
    it.run("b = a")
    it.run("v = a[1:3]")
    run(it, "a(2) = 5; a(3) = 6; r = b(2); q = v(2);")
    assert (val(it, "r"), val(it, "q")) == (0, 0)


def test_the_workspace_seen_between_commands_stays_put(it):
    """Something outside the console (a plot, the workspace pane, a model)
    may keep the array it read; the next command must not change it."""
    run(it, OWN)
    held = val(it, "a")
    run(it, "a(2) = 9;")
    assert same(held, [1, 0, 0, 0])
    held = val(it, "a")
    run(it, "for k = 1:3, a(k) = -k; end")
    assert same(held, [1, 9, 0, 0])
    assert same(val(it, "a"), [-1, -2, -3, 0])


# ──────────────────────────────────────────────────────────────
#  Functions, anonymous functions, globals, persistents
# ──────────────────────────────────────────────────────────────

def test_a_function_writing_its_argument_leaves_the_callers(it, tmp_path):
    where = folder(tmp_path, bump="function r = bump(x)\nx(1) = 9;\n"
                   "x(2) = 8;\nr = x;\nend\n")
    run(it, f"addpath('{where}'); " + OWN + "d = bump(a); r = a(1) + a(2);")
    assert val(it, "r") == 1
    assert same(val(it, "d"), [9, 8, 0, 0])


def test_a_functions_result_is_its_own(it, tmp_path):
    """A function that returns its argument: writing the caller's array
    after the call must not reach the result."""
    where = folder(tmp_path, keep="function r = keep(x)\nr = x;\nend\n",
                   two="function [x, y] = two()\nx = zeros(1,3); x(1) = 1;"
                       "\ny = x;\nend\n")
    run(it, f"addpath('{where}'); " + OWN + "d = keep(a); a(2) = 9; "
            "r = d(2); [p, q] = two(); p(2) = 9; s = q(2);")
    assert (val(it, "r"), val(it, "s")) == (0, 0)


def test_a_local_function_in_the_fill_loop(it):
    run(it, "a = zeros(1,3);\nfor k = 1:3\n  a(k) = sq(a, k);\nend\n"
            "function y = sq(v, k)\n  v(k) = 100;\n  y = k^2;\nend\n")
    assert same(val(it, "a"), [1, 4, 9])


def test_an_anonymous_function_keeps_the_array_it_was_made_with(it):
    run(it, OWN + "f = @() a(2); g = @(i) a(i); "
            "for k = 1:3, a(2) = k; a(3) = k; end; r = f(); q = g(3);")
    assert (val(it, "r"), val(it, "q")) == (0, 0)


def test_a_global_array(it, tmp_path):
    """A global is one value seen from every function that declares it: a
    write in one is seen in the other. A copy taken from it is not."""
    where = folder(tmp_path,
                   setg="function setg(k, v)\nglobal G\nG(k) = v;\nend\n",
                   readg="function v = readg()\nglobal G\nv = G;\nend\n")
    run(it, f"addpath('{where}'); global G; G = zeros(1,3); "
            "setg(1, 5); setg(2, 6); r = readg(); b = G; setg(3, 7); "
            "q = b(3); w = G;")
    assert same(val(it, "r"), [5, 6, 0])
    assert val(it, "q") == 0
    assert same(val(it, "w"), [5, 6, 7])


def test_a_persistent_array(it, tmp_path):
    where = folder(tmp_path, acc="function out = acc(k)\npersistent p\n"
                   "if isempty(p)\n  p = zeros(1,3);\nend\np(k) = k;\n"
                   "out = p;\nend\n")
    run(it, f"addpath('{where}'); x = acc(1); y = acc(2); z = acc(3); "
            "x(3) = 9; w = acc(1);")
    assert same(val(it, "x"), [1, 0, 9])
    assert same(val(it, "y"), [1, 2, 0])
    assert same(val(it, "z"), [1, 2, 3])
    assert same(val(it, "w"), [1, 2, 3])


def test_ans_is_its_own_value(it):
    run(it, OWN + "double(a); a(2) = 9; r = ans(2);")
    assert val(it, "r") == 0
    run(it, OWN + "double(a); ans(2) = 9; r = a(2);")
    assert val(it, "r") == 0


def test_a_for_loop_takes_the_array_as_it_was(it):
    """``for v = a`` walks the array the loop started with, whatever the body
    writes to ``a``; and a column it handed out stays as it was."""
    run(it, OWN + "w = []; for v = a, a(2) = 9; a(3) = 8; w(end+1) = v; end")
    assert same(val(it, "w"), [1, 0, 0, 0])
    run(it, "A = zeros(2); A(1) = 1; for v = A, A(2,2) = 9; last = v; end; "
            "r = last(2); for u = A, end; A(1,2) = 7; q = u(1);")
    assert val(it, "r") == 0
    assert val(it, "q") == 0


# ──────────────────────────────────────────────────────────────
#  Maps, tables, objects
# ──────────────────────────────────────────────────────────────

def test_a_containers_map_value(it):
    run(it, "m = containers.Map(); " + OWN + "m('k') = a; a(2) = 9; "
            "x = m('k'); r = x(2); x(3) = 9; y = m('k'); q = y(3);")
    assert (val(it, "r"), val(it, "q")) == (0, 0)


def test_a_containers_map_built_with_the_array(it):
    run(it, OWN + "m = containers.Map({'k'}, {a}); a(2) = 9; x = m('k'); "
            "r = x(2);")
    assert val(it, "r") == 0


def test_varargin_written_in_the_function(it, tmp_path):
    where = folder(tmp_path, vf="function r = vf(varargin)\n"
                   "varargin{1}(1) = 9;\nvarargin{1}(2) = 8;\n"
                   "r = varargin{1};\nend\n")
    run(it, f"addpath('{where}'); " + OWN + "d = vf(a); r = a(1) + a(2);")
    assert val(it, "r") == 1
    assert same(val(it, "d"), [9, 8, 0, 0])


def test_a_nested_function_shares_its_parents_array(it, tmp_path):
    """A nested function's variables are its parent's: it sees the writes
    the parent makes after the handle to it was taken, and its own writes
    reach the parent."""
    where = folder(tmp_path, nest="function r = nest()\n"
                   "a = zeros(1,3); a(1) = 1;\nf = @get2;\na(2) = 5;\n"
                   "bump();\nr = [f(), a(3)];\n"
                   "  function v = get2()\n    v = a(2);\n  end\n"
                   "  function bump()\n    a(3) = 7;\n  end\nend\n")
    run(it, f"addpath('{where}'); r = nest();")
    assert same(val(it, "r"), [5, 7])


def test_a_table_variable(it):
    run(it, "a = zeros(3,1); a(1) = 1; t = table(a); a(2) = 9; x = t.a; "
            "r = x(2); t.b = a; a(3) = 7; y = t.b; q = y(3); "
            "x(1) = 5; z = t.a; p = z(1);")
    assert (val(it, "r"), val(it, "q"), val(it, "p")) == (0, 0, 1)


BOX = "classdef Box\n  properties\n    v\n  end\nend\n"
HBOX = "classdef HBox < handle\n  properties\n    v\n  end\nend\n"
CHECKED = """\
classdef Checked < handle
  properties
    v = zeros(1,3)
  end
  methods
    function set.v(obj, x)
      if any(x < 0)
        error('no negatives');
      end
      obj.v = x;
    end
  end
end
"""


def test_a_value_objects_property(it, tmp_path):
    where = folder(tmp_path, Box=BOX)
    run(it, f"addpath('{where}'); b = Box(); " + OWN + "b.v = a; a(2) = 9; "
            "r = b.v(2); b.v(3) = 7; q = a(3); c = b; b.v(1) = 5; "
            "p = c.v(1); c.v(4) = 6; o = b.v(4);")
    assert (val(it, "r"), val(it, "q"), val(it, "p"), val(it, "o")) == \
        (0, 0, 1, 0)


def test_a_handle_objects_property(it, tmp_path):
    """A handle object is one object: a write through any variable that
    holds it is seen through all of them. A copy of the property is not."""
    where = folder(tmp_path, HBox=HBOX)
    run(it, f"addpath('{where}'); h = HBox(); h.v = zeros(1,3); h.v(1) = 1; "
            "x = h.v; h.v(2) = 9; r = x(2); h2 = h; h2.v(3) = 7; "
            "q = h.v(3);")
    assert (val(it, "r"), val(it, "q")) == (0, 7)


def test_a_property_setter_sees_the_old_value(it, tmp_path):
    """A ``set.v`` that refuses a value must leave the property as it was."""
    where = folder(tmp_path, Checked=CHECKED)
    run(it, f"addpath('{where}'); h = Checked(); h.v(1) = 1; "
            "try, h.v(2) = -1; catch, end; r = h.v;")
    assert same(val(it, "r"), [1, 0, 0])


# ──────────────────────────────────────────────────────────────
#  What a write does to the array itself: unchanged by the speed-up
# ──────────────────────────────────────────────────────────────

def test_an_integer_array_saturates_and_keeps_its_class(it):
    run(it, "a = zeros(1,3,'int8'); a(1) = 1; a(2) = 300; a(3) = -2.6; "
            "c = class(a);")
    assert same(val(it, "a"), [1, 127, -3])
    assert val(it, "c") == "int8"


def test_a_double_array_that_takes_an_integer_becomes_one(it):
    run(it, "a = zeros(1,3); a(1) = 1.7; a(2) = int8(5); c = class(a);")
    assert val(it, "c") == "int8"
    assert same(val(it, "a"), [2, 5, 0])


def test_a_complex_value_makes_the_array_complex(it):
    run(it, OWN + "a(2) = 1i; a(3) = 2;")
    assert same(val(it, "a"), [1, 1j, 2, 0])


def test_logical_and_single_arrays(it):
    run(it, "a = logical([0 0 0]); a(1) = true; a(2) = 5; c = class(a); "
            "g = zeros(1,3,'single'); g(1) = 1; g(2) = 0.1; d = class(g);")
    assert val(it, "c") == "double"
    assert same(val(it, "a"), [1, 5, 0])
    assert val(it, "d") == "single"
    assert val(it, "g")[1] == np.float32(0.1)


def test_growing_and_writing_past_the_end(it):
    run(it, "a = []; for k = 1:5, a(end+1) = k; end; "
            "b = zeros(1,2); b(1) = 1; b(5) = 3; "
            "c = zeros(3,1); c(1) = 1; c(5) = 2; cz = size(c); "
            "M = zeros(2); M(1) = 1; M(3,3) = 9;")
    assert same(val(it, "a"), [1, 2, 3, 4, 5])
    assert same(val(it, "b"), [1, 0, 0, 0, 3])
    assert same(val(it, "cz"), [5, 1])
    assert same(val(it, "M"), [[1, 0, 0], [0, 0, 0], [0, 0, 9]])


def test_deleting(it):
    run(it, "a = 1:5; a(1) = 0; a(2) = []; "
            "M = magic(3); M(1) = 0; M(:, 2) = []; ")
    assert same(val(it, "a"), [0, 3, 4, 5])
    assert same(val(it, "M"), [[0, 6], [3, 7], [4, 2]])


def test_matrix_writes(it):
    run(it, "A = zeros(2,3); A(1) = 1; A(4) = 4; A(2,3) = 6; "
            "A(:,1) = [7;8]; B = zeros(3,4); "
            "for k = 1:4, B(:,k) = (1:3)'*k; end")
    assert same(val(it, "A"), [[7, 0, 0], [8, 4, 6]])
    assert same(val(it, "B"), np.outer([1, 2, 3], [1, 2, 3, 4]))


def test_nd_arrays(it):
    run(it, "A = zeros(2,2,2); A(1,1,1) = 1; A(2,2,2) = 8; B = A; "
            "A(1,2,2) = 5; r = B(1,2,2); q = A(1,2,2); A(7) = 3; s = A(1,2,2);")
    assert (val(it, "r"), val(it, "q"), val(it, "s")) == (0, 5, 3)


def test_scalar_writes_of_every_kind(it):
    """The quick route for ``a(i) = v`` and its edges, each against the
    value MATLAB gives."""
    run(it, "a = zeros(1,3); a(1) = 1; a(2) = NaN; a(3) = -Inf; "
            "b = zeros(1,3); b(1) = 1; b(1,2) = 5; b(1,3) = 2^60; "
            "z = zeros(2); z(1) = 1; z(2,1) = 1i; z(4) = 3; "
            "c = zeros(1,3) + 1i; c(1) = 2; c(2) = 0; "
            "m = zeros(2,3); m(1) = 1; m(5) = 7; m(2,3) = 8; "
            "n = zeros(2,2,2); n(1) = 1; n(8) = 8; n(1,2,2) = 6; "
            "w = zeros(3,1); w(1) = 1; w(3,1) = 4; w(2) = true; "
            "wc = class(w); u = zeros(1,3); u(1) = 1; u(2) = int16(7); "
            "uc = class(u);")
    v = it.namespace
    assert v["a"][0] == 1 and np.isnan(v["a"][1]) and v["a"][2] == -np.inf
    assert same(v["b"], [1, 5, 2.0 ** 60])
    assert same(v["z"], [[1, 0], [1j, 3]])
    assert same(v["c"], [2, 0, 1j])
    assert same(v["m"], [[1, 0, 7], [0, 0, 8]])
    assert same(v["n"][:, :, 1], [[0, 6], [0, 8]])
    assert v["n"][0, 0, 0] == 1
    assert same(v["w"], [1, 1, 4]) and v["wc"] == "double"
    assert same(v["u"], [1, 7, 0]) and v["uc"] == "int16"


def test_out_of_range_and_bad_subscripts_still_fail_or_grow(it):
    run(it, "a = zeros(1,3); a(1) = 1; a(1, 5) = 2; "
            "M = zeros(2); M(1) = 1; M(3, 1) = 4;")
    assert same(val(it, "a"), [1, 0, 0, 0, 2])
    assert same(val(it, "M"), [[1, 0], [0, 0], [4, 0]])
    for bad in ("a(0) = 1;", "a(1.5) = 1;", "a(-1) = 1;", "a(NaN) = 1;"):
        results = it.run_script(OWN + bad, "matlab")
        assert any(r.error for r in results), bad
        assert same(val(it, "a"), [1, 0, 0, 0]), bad


def test_a_failed_write_leaves_the_array_as_it_was(it):
    run(it, OWN + "try, a(1:2) = [1 2 3]; catch, end; "
            "try, a(0) = 5; catch, end; try, a(1.5) = 5; catch, end; "
            "M = zeros(2); M(1) = 1; try, M(:, 1) = [1 2 3]; catch, end")
    assert same(val(it, "a"), [1, 0, 0, 0])
    assert same(val(it, "M"), [[1, 0], [0, 0]])


# ──────────────────────────────────────────────────────────────
#  Speed: linear, not quadratic
# ──────────────────────────────────────────────────────────────

def _fill_time(it, n: int) -> float:
    t0 = time.perf_counter()
    run(it, f"a = zeros(1, {n}); for k = 1:{n}, a(k) = k^2 + numel(a); end")
    elapsed = time.perf_counter() - t0
    assert val(it, "a")[-1] == n * n + n
    return elapsed


def test_filling_a_preallocated_vector_is_linear(it):
    """
    Each write used to copy the vector: 10⁴ writes took about 0.4 s and 10⁵
    about a minute. Timed against the same loop doing no array work, and 4×
    the length against 1×, so a slow machine slows both sides.
    """
    t0 = time.perf_counter()
    run(it, "for k = 1:20000, z = k^2 + k; end")
    plain = time.perf_counter() - t0
    small = _fill_time(it, 5000)
    large = _fill_time(it, 20000)
    assert large < 8 * small + 0.2            # quadratic would be 16×
    assert large < 10 * plain + 1.5


def _writes_time(it, setup: str, write: str, count: int = 200) -> float:
    run(it, setup)
    t0 = time.perf_counter()
    run(it, f"for k = 1:{count}, j = mod(k - 1, 20) + 1; {write}; end")
    return time.perf_counter() - t0


@pytest.mark.parametrize("small, large, write", [
    ("a = zeros(1, 1000);", "a = zeros(1, 2e6);", "a(j) = k"),
    ("a = zeros(1000, 1);", "a = zeros(2e6, 1);", "a(j) = k"),
    ("A = zeros(30);", "A = zeros(1500);", "A(j, 3) = k"),
    ("A = zeros(1500, 30);", "A = zeros(1500);", "A(:, j) = k"),
    ("A = zeros(30);", "A = zeros(1500);", "A(j) = k"),
    ("A = zeros(30, 30, 30);", "A = zeros(150, 150, 100);",
     "A(j, 2, 3) = k"),
], ids=["row", "column", "A(i,j)", "A(:,k)", "A(k)", "N-D"])
def test_a_write_costs_the_same_whatever_the_arrays_size(it, small, large,
                                                         write):
    """
    The same 200 writes into a small array and into a 16 MB one. Copying
    the array at each write made the large one take seconds; in place, both
    are a loop of 200 writes (and one copy, the first write's).
    """
    fast = _writes_time(it, small, write)
    slow = _writes_time(it, large, write)
    assert slow < 3 * fast + 0.15
