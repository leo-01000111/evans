"""
Cells and structs: cellfun, arrayfun, cell2mat, struct2cell, cell2struct,
rmfield, orderfields, isequal, ismember, deal and the small ones.

Each test types the command the way a user would and checks it against values
worked out by hand from MATLAB's documented behaviour, never against what
Evans printed.
"""

from __future__ import annotations

import numpy as np
import pytest

from evans.console import Interpreter, set_figure_sink
from evans.console import matlab_runtime as _mr
from evans.console.figures import recording_sink
from evans.console.matlab_runtime import Cell, Struct, StructArray

CellLibrary = _mr.CellLibrary          # the runtime imports its mixins first


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


def size_of(it, name):
    run(it, f"sz__ = size({name});")
    return tuple(int(v) for v in np.ravel(val(it, "sz__")))


# ──────────────────────────────────────────────────────────────
#  cellfun
# ──────────────────────────────────────────────────────────────

def test_cellfun_keeps_the_shape_of_a_2x2_cell(it):
    """numel of 1, [1 2 3], 'ab', [] is 1, 3, 2, 0, laid out as the cell."""
    run(it, "c = {1,[1 2 3];'ab',[]}; n = cellfun(@numel, c);")
    assert size_of(it, "n") == (2, 2)
    assert np.asarray(val(it, "n")).tolist() == [[1, 3], [2, 0]]


@pytest.mark.parametrize("source, shape", [
    ("{1,2,3}", (1, 3)), ("{1;2;3}", (3, 1)), ("{1}", (1, 1)),
])
def test_cellfun_row_column_and_scalar(it, source, shape):
    """A row cell gives a row, a column a column, one element a scalar."""
    run(it, f"y = cellfun(@(x) x*2, {source});")
    assert size_of(it, "y") == shape
    assert np.ravel(val(it, "y")).tolist()[0] == 2


def test_cellfun_isempty_is_logical(it):
    """isempty of 1, [], 'a' is false, true, false — a logical row."""
    run(it, "e = cellfun(@isempty, {1,[],'a'}); k = class(e);")
    assert np.ravel(val(it, "e")).tolist() == [False, True, False]
    assert val(it, "k") == "logical"


def test_cellfun_legacy_strings(it):
    """The string forms: length 1, 3, 2; prodofsize of a 2×3 is 6; isclass."""
    run(it, "c = {1,[1 2 3],'ab'}; n = cellfun('length', c); "
            "e = cellfun('isempty', {[], 1}); p = cellfun('prodofsize', "
            "{zeros(2,3)}); q = cellfun('isclass', c, 'char'); "
            "z = cellfun('size', {zeros(2,3), 1}, 1); d = cellfun('ndims', c);")
    assert np.ravel(val(it, "n")).tolist() == [1, 3, 2]
    assert np.ravel(val(it, "e")).tolist() == [True, False]
    assert val(it, "p") == 6
    assert np.ravel(val(it, "q")).tolist() == [False, False, True]
    assert np.ravel(val(it, "z")).tolist() == [2, 1]
    assert np.ravel(val(it, "d")).tolist() == [2, 2, 2]


def test_cellfun_two_outputs_from_max(it):
    """max of [1 5 2] is 5 at 2; of [7 3] is 7 at 1."""
    run(it, "[m, k] = cellfun(@max, {[1 5 2], [7 3]});")
    assert np.ravel(val(it, "m")).tolist() == [5, 7]
    assert np.ravel(val(it, "k")).tolist() == [2, 1]


def test_cellfun_two_inputs(it):
    """Elementwise over two cells: 1+10, 2+20."""
    run(it, "s = cellfun(@(a, b) a + b, {1, 2}, {10, 20});")
    assert np.ravel(val(it, "s")).tolist() == [11, 22]


def test_cellfun_uniform_output_false_gives_a_cell(it):
    """Non-scalar results go into a cell of the input's shape."""
    run(it, "y = cellfun(@(x) [x x], {1; 2}, 'UniformOutput', false); "
            "a = y{2};")
    assert size_of(it, "y") == (2, 1)
    assert np.ravel(val(it, "a")).tolist() == [2, 2]


def test_cellfun_char_results_make_a_char_row(it):
    """upper of 'a', 'b' is 'A', 'B': uniform chars concatenate to 'AB'."""
    run(it, "u = cellfun(@upper, {'a','b'});")
    assert val(it, "u") == "AB"


def test_cellfun_empty_cell(it):
    """Nothing to map over: MATLAB returns [] (0×0)."""
    run(it, "w = cellfun(@numel, {});")
    assert size_of(it, "w") == (0, 0)


def test_cellfun_refusals(it):
    """MATLAB's errors: non-scalar, mixed classes, sizes, ErrorHandler."""
    msg = error_of(it, "cellfun(@(x) [x x], {1,2})")
    assert "Non-scalar in Uniform output, at index 1, output 1" in msg
    assert "UniformOutput" in msg
    msg = error_of(it, "cellfun(@(x) x, {1, true})")
    assert "Mismatch in type of outputs, at index 2" in msg
    assert "same size" in error_of(it, "cellfun(@numel, {1,2}, {1})")
    assert "ErrorHandler" in error_of(
        it, "cellfun(@(x) x, {1}, 'ErrorHandler', @(e, x) 0)")
    assert "cell" in error_of(it, "cellfun(@numel, [1 2])")
    assert "Too many output" in error_of(it, "[a, b] = cellfun(@numel, {1})")


# ──────────────────────────────────────────────────────────────
#  arrayfun
# ──────────────────────────────────────────────────────────────

def test_arrayfun_over_a_matrix_keeps_its_shape(it):
    """Squares of [1 2; 3 4] are [1 4; 9 16]; a column stays a column."""
    run(it, "a = arrayfun(@(x) x^2, [1 2; 3 4]); b = arrayfun(@(x) x^2, "
            "[1; 2; 3]);")
    assert np.asarray(val(it, "a")).tolist() == [[1, 4], [9, 16]]
    assert size_of(it, "b") == (3, 1)
    assert np.ravel(val(it, "b")).tolist() == [1, 4, 9]


def test_arrayfun_over_a_struct_array(it):
    """Each element is a struct: fields a = 1, 5 → 10, 50."""
    run(it, "s(1).a = 1; s(2).a = 5; v = arrayfun(@(e) e.a * 10, s);")
    assert np.ravel(val(it, "v")).tolist() == [10, 50]


def test_arrayfun_over_char_and_logical(it):
    """Each char is a 1-char string; each logical stays logical."""
    run(it, "u = arrayfun(@(c) upper(c), 'abc'); "
            "n = arrayfun(@(b) ~b, [true false]);")
    assert val(it, "u") == "ABC"
    assert np.ravel(val(it, "n")).tolist() == [False, True]


def test_arrayfun_two_inputs_and_two_outputs(it, tmp_path):
    """x+y of [1 2], [10 20] is [11 22]; a two-output file function gives x
    and x^2 of 3, 1, 2."""
    (tmp_path / "twice.m").write_text(
        "function [a, b] = twice(x)\na = x;\nb = x^2;\nend\n")
    run(it, f"cd('{tmp_path.as_posix()}'); "
            "s = arrayfun(@(x, y) x + y, [1 2], [10 20]); "
            "[m, k] = arrayfun(@twice, [3 1 2]);")
    assert np.ravel(val(it, "s")).tolist() == [11, 22]
    assert np.ravel(val(it, "m")).tolist() == [3, 1, 2]
    assert np.ravel(val(it, "k")).tolist() == [9, 1, 4]


def test_arrayfun_building_structs_and_cells(it):
    """struct outputs make a 1×3 struct array; 'UniformOutput' false a cell."""
    run(it, "q = arrayfun(@(x) struct('a', x), 1:3); qa = q(3).a; "
            "c = arrayfun(@(x) 1:x, 1:3, 'UniformOutput', false); "
            "c3 = c{3};")
    assert size_of(it, "q") == (1, 3)
    assert val(it, "qa") == 3
    assert np.ravel(val(it, "c3")).tolist() == [1, 2, 3]


def test_arrayfun_over_a_cell_passes_one_by_one_cells(it):
    """arrayfun over a cell gives the function c(i), a 1×1 cell."""
    run(it, "k = arrayfun(@(x) iscell(x), {1, 'a'});")
    assert np.ravel(val(it, "k")).tolist() == [True, True]


def test_arrayfun_refuses_non_scalar(it):
    """1:x is not a scalar for x = 2."""
    msg = error_of(it, "arrayfun(@(x) 1:x, [1 2])")
    assert "Non-scalar in Uniform output, at index 2, output 1" in msg


# ──────────────────────────────────────────────────────────────
#  cell2mat, struct2cell, cell2struct
# ──────────────────────────────────────────────────────────────

def test_cell2mat_joins_blocks(it):
    """Rows of blocks side by side, then stacked: [1 2 3; 4 5 6]."""
    run(it, "m = cell2mat({[1 2], 3; [4 5], 6}); "
            "v = cell2mat({[1; 2], [3; 4]}); t = cell2mat({'ab', 'cd'});")
    assert np.asarray(val(it, "m")).tolist() == [[1, 2, 3], [4, 5, 6]]
    assert np.asarray(val(it, "v")).tolist() == [[1, 3], [2, 4]]
    assert val(it, "t") == "abcd"


def test_cell2mat_refusals(it):
    """MATLAB's errors for cells of cells, mixed classes, bad sizes."""
    assert "does not support cell arrays containing cell arrays" in \
        error_of(it, "cell2mat({{1}})")
    assert "same data type" in error_of(it, "cell2mat({1, true})")
    assert "not consistent" in error_of(it, "cell2mat({[1 2]; 3})")


def test_struct2cell_is_a_column_of_values_in_field_order(it):
    """Fields b = 2 then a = 'x' → {2; 'x'}, 2×1."""
    run(it, "t.b = 2; t.a = 'x'; c = struct2cell(t); c2 = c{2};")
    assert size_of(it, "c") == (2, 1)
    assert val(it, "c2") == "x"


def test_struct2cell_of_struct_arrays(it):
    """
    A 1×2 struct array gives n×1×2 (3-D) in MATLAB, which Evans cannot hold;
    a 2×1 one gives n×2, a column of values per element.
    """
    assert "2-D" in error_of(it, "s(1).a = 1; s(2).a = 2; struct2cell(s)")
    run(it, "q = struct('a', {1; 2}, 'b', 'z'); c = struct2cell(q); "
            "c12 = c{1, 2}; c22 = c{2, 2};")
    assert size_of(it, "c") == (2, 2)
    assert (val(it, "c12"), val(it, "c22")) == (2, "z")


def test_cell2struct_along_either_dimension(it):
    """{'Bob'; 30} with dim 1 and {'Bob', 30} with dim 2 both give one struct."""
    run(it, "p = cell2struct({'Bob'; 30}, {'name'; 'age'}, 1); "
            "q = cell2struct({'Bob', 30}, {'name', 'age'}, 2); "
            "pn = p.name; qa = q.age;")
    assert val(it, "pn") == "Bob"
    assert val(it, "qa") == 30
    run(it, "r = cell2struct({1, 2; 'x', 'y'}, {'n'; 't'}, 1); r2 = r(2).t;")
    assert size_of(it, "r") == (2, 1)                  # one per column
    assert val(it, "r2") == "y"
    msg = error_of(it, "cell2struct({1; 2}, {'a'}, 1)")
    assert "Number of field names must match" in msg


# ──────────────────────────────────────────────────────────────
#  rmfield, orderfields, isfield, getfield, setfield
# ──────────────────────────────────────────────────────────────

def test_rmfield_one_name_or_several(it):
    """Removing b leaves a and c; removing {a, c} leaves b; s is unchanged."""
    run(it, "s.a = 1; s.b = 2; s.c = 3; r = rmfield(s, 'b'); "
            "q = rmfield(s, {'a', 'c'}); fr = fieldnames(r); "
            "fq = fieldnames(q); fs = fieldnames(s);")
    assert list(val(it, "fr")) == ["a", "c"]
    assert list(val(it, "fq")) == ["b"]
    assert list(val(it, "fs")) == ["a", "b", "c"]
    assert "A field named 'z' doesn't exist." in error_of(
        it, "rmfield(s, 'z')")


def test_orderfields_ascii_order_and_permutation(it):
    """b, B, a sort to B, a, b (uppercase first); perm is [2; 3; 1]."""
    run(it, "u.b = 1; u.B = 2; u.a = 3; [o, p] = orderfields(u); "
            "f = fieldnames(o);")
    assert list(val(it, "f")) == ["B", "a", "b"]
    assert size_of(it, "p") == (3, 1)
    assert np.ravel(val(it, "p")).tolist() == [2, 3, 1]


def test_orderfields_by_names_and_by_permutation(it):
    """Explicit orders: {'c','a','b'} and [3 1 2] both give c, a, b."""
    run(it, "s.a = 1; s.b = 2; s.c = 3; x = orderfields(s, {'c','a','b'}); "
            "y = orderfields(s, [3 1 2]); fx = fieldnames(x); "
            "fy = fieldnames(y); yc = y.c;")
    assert list(val(it, "fx")) == ["c", "a", "b"]
    assert list(val(it, "fy")) == ["c", "a", "b"]
    assert val(it, "yc") == 3
    assert "exactly the fields" in error_of(it, "orderfields(s, {'a','b'})")


def test_isfield_with_a_cell_of_names():
    """
    The mixin's isfield (it replaces ``_Library.f_isfield`` once that is
    removed): a cell of names gives a logical of the cell's shape, and a
    struct array is a struct too.
    """
    lib = CellLibrary()
    s = Struct(a=1, b=2)
    hits = lib.f_isfield(s, Cell(["a", "z", "b"]))
    assert np.ravel(hits).tolist() == [True, False, True]
    assert lib.f_isfield(StructArray([s, s]), "b") is True
    assert lib.f_isfield(5, "a") is False


def test_getfield_and_setfield(it):
    """Nested setfield writes s.p.q = 4 without touching the original."""
    run(it, "s.a = 'x'; g = getfield(s, 'a'); t = setfield(s, 'p', 'q', 4); "
            "tq = t.p.q; has = isfield(s, 'p');")
    assert val(it, "g") == "x"
    assert val(it, "tq") == 4
    assert val(it, "has") is False


# ──────────────────────────────────────────────────────────────
#  isequal, isequaln
# ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("source, expected", [
    ("isequal('a', 97)", True),                 # char compares by code
    ("isequal([1 2], [1; 2])", False),          # row vs column
    ("isequal(1, true)", True),
    ("isequal(NaN, NaN)", False),
    ("isequaln(NaN, NaN)", True),
    ("isequaln([1 NaN], [1 NaN], [1 NaN])", True),
    ("isequal([1 2 3], [1 2 3], [1 2 4])", False),
    ("isequal(struct('a', 1, 'b', 2), struct('b', 2, 'a', 1))", True),
    ("isequal(struct('a', 1), struct('a', 1, 'b', 2))", False),
    ("isequal({1, 'x'}, {1, 'x'})", True),
    ("isequal({1, 'x'}, {1; 'x'})", False),
    ("isequal({1, {2}}, {1, {3}})", False),
    ("isequal('abc', 'abc')", True),
    ("isequal('', [])", True),
    ("isequal({1}, 1)", False),
])
def test_isequal(it, source, expected):
    """MATLAB's rules: values and sizes; NaN unequal unless isequaln."""
    run(it, f"r = {source};")
    assert bool(val(it, "r")) is expected


# ──────────────────────────────────────────────────────────────
#  ismember
# ──────────────────────────────────────────────────────────────

def test_ismember_numeric_with_lowest_index(it):
    """1 is at 2 and 3 (lowest 2), 5 absent, 2 at 1, 9 absent."""
    run(it, "[tf, loc] = ismember([1 5 2 9], [2 1 1 7]);")
    assert np.ravel(val(it, "tf")).tolist() == [True, False, True, False]
    assert np.ravel(val(it, "loc")).tolist() == [2, 0, 1, 0]


def test_ismember_has_the_shape_of_a(it):
    """A 2×2 a gives a 2×2 tf; NaN is a member of nothing."""
    run(it, "tf = ismember([1 2; NaN 4], [4 NaN 1]);")
    assert np.asarray(val(it, "tf")).tolist() == [[True, False],
                                                  [False, True]]


def test_ismember_text(it):
    """'b' is in {'a','b'} at 2; cellstr vs cellstr elementwise."""
    run(it, "[t1, l1] = ismember('b', {'a','b'}); "
            "[tf, loc] = ismember({'a','z','b'}, {'b','a'}); "
            "t3 = ismember('abc', 'cb');")
    assert val(it, "t1") is True and val(it, "l1") == 2
    assert np.ravel(val(it, "tf")).tolist() == [True, False, True]
    assert np.ravel(val(it, "loc")).tolist() == [2, 0, 1]
    assert np.ravel(val(it, "t3")).tolist() == [False, True, True]


def test_ismember_rows_and_refusal(it):
    """Row [1 2] is in S, [3 4] is not; a cell of numbers is refused."""
    run(it, "[tf, loc] = ismember([1 2; 3 4], [5 6; 1 2], 'rows');")
    assert size_of(it, "tf") == (2, 1)
    assert np.ravel(val(it, "loc")).tolist() == [2, 0]
    assert "cell arrays of character vectors" in error_of(
        it, "ismember({1}, {1, 2})")


# ──────────────────────────────────────────────────────────────
#  deal, iscellstr
# ──────────────────────────────────────────────────────────────

def test_deal(it):
    """deal(1, 2) hands out each input; deal(7) copies it to every output."""
    run(it, "[a, b] = deal(1, 2); [c, d] = deal(7);")
    assert (val(it, "a"), val(it, "b")) == (1, 2)
    assert (val(it, "c"), val(it, "d")) == (7, 7)
    assert "number of outputs" in error_of(it, "[x, y] = deal(1, 2, 3)")


def test_iscellstr(it):
    """Only cells whose every element is a char vector; {} counts."""
    run(it, "a = iscellstr({'a','b'}); b = iscellstr({'a', 1}); "
            "c = iscellstr('a'); d = iscellstr({});")
    assert (val(it, "a"), val(it, "b"), val(it, "c"), val(it, "d")) == \
        (True, False, False, True)
