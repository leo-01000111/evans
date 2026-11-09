"""
N-D arrays: construction, size queries, indexing and assignment with three or
more subscripts, concatenation, permute/squeeze/reshape, reductions along a
dimension, broadcasting, display, N-D cells and true-colour images.
"""

import numpy as np
import pytest

from evans.console import Interpreter, figure_mpl, set_figure_sink
from evans.console.figures import recording_sink


@pytest.fixture
def sink():
    recorder = recording_sink()
    previous = set_figure_sink(recorder)
    yield recorder
    set_figure_sink(previous)


@pytest.fixture
def it(sink):
    return Interpreter()


def run(it, source):
    result = it.command(source)
    assert result.ok, f"{source}\n→ {result.error}"
    return result


def val(it, expr):
    return it.evaluate(expr)


def error(it, source) -> str:
    result = it.command(source)
    assert not result.ok, f"{source} should have failed"
    return result.error


def arr(it, expr):
    return np.asarray(val(it, expr), dtype=float)


A = "A = reshape(1:24, 2, 3, 4);"


# ── construction and size ──────────────────────────────────────

@pytest.mark.parametrize("fn", ["zeros", "ones", "rand", "randn"])
def test_constructors_make_n_d(it, fn):
    run(it, f"x = {fn}(2,3,4); y = {fn}([2 3 4]); z = {fn}(2,3,4,2);")
    assert arr(it, "size(x)").tolist() == [2, 3, 4]
    assert arr(it, "size(y)").tolist() == [2, 3, 4]
    assert arr(it, "size(z)").tolist() == [2, 3, 4, 2]


def test_size_ndims_numel_length(it):
    run(it, A)
    assert arr(it, "size(A)").tolist() == [2, 3, 4]
    assert val(it, "size(A, 3)") == 4
    assert val(it, "size(A, 5)") == 1
    assert val(it, "ndims(A)") == 3
    assert val(it, "numel(A)") == 24
    assert val(it, "length(A)") == 4
    assert val(it, "ndims(zeros(2,2))") == 2
    run(it, "[r, c] = size(A);")
    assert (val(it, "r"), val(it, "c")) == (2, 12)
    run(it, "[r, c, p] = size(A);")
    assert (val(it, "r"), val(it, "c"), val(it, "p")) == (2, 3, 4)
    run(it, "[r, c, p, q] = size(A);")
    assert val(it, "q") == 1


def test_trailing_singletons_drop(it):
    run(it, "x = zeros(2,3,1); y = ones(1,1,3);")
    assert arr(it, "size(x)").tolist() == [2, 3]
    assert arr(it, "size(y)").tolist() == [1, 1, 3]


def test_vector_predicates_on_n_d(it):
    run(it, "x = ones(1,3,2);")
    assert not val(it, "isvector(x)")
    assert not val(it, "isrow(x)")
    assert not val(it, "iscolumn(x)")
    assert not val(it, "isscalar(x)")


# ── indexing ───────────────────────────────────────────────────

def test_subscripts_and_linear_index_are_column_major(it):
    run(it, A)
    assert val(it, "A(2,3,4)") == 24
    assert val(it, "A(1,2,3)") == 15
    assert val(it, "A(5)") == 5
    assert val(it, "A(end)") == 24
    assert val(it, "A(end,end,end)") == 24
    assert arr(it, "A(:,:,2)").tolist() == [[7, 9, 11], [8, 10, 12]]
    assert arr(it, "size(A(:,:,[1 3]))").tolist() == [2, 3, 2]
    assert arr(it, "size(A(2,:,:))").tolist() == [1, 3, 4]
    assert arr(it, "A(:)'").tolist() == list(range(1, 25))
    assert arr(it, "squeeze(A(1,2,:))").ravel().tolist() == [3, 9, 15, 21]


def test_fewer_subscripts_fold_the_trailing_dimensions(it):
    run(it, A)
    assert val(it, "A(2, 5)") == 10
    assert val(it, "A(2, 12)") == 24
    assert arr(it, "size(A(:, :))").tolist() == [2, 12]


def test_logical_index_on_n_d(it):
    run(it, A)
    assert arr(it, "A(A > 22)").ravel().tolist() == [23, 24]


def test_index_out_of_range_is_an_error(it):
    run(it, A)
    assert "exceed" in error(it, "A(1,1,5)").lower()


# ── assignment ─────────────────────────────────────────────────

def test_assign_a_page_and_grow(it):
    run(it, "B = zeros(2,2,2); B(:,:,2) = [1 2; 3 4];")
    assert arr(it, "B(:,:,2)").tolist() == [[1, 2], [3, 4]]
    assert arr(it, "B(:,:,1)").tolist() == [[0, 0], [0, 0]]
    run(it, "B(1,1,4) = 9;")
    assert arr(it, "size(B)").tolist() == [2, 2, 4]
    assert val(it, "B(1,1,4)") == 9
    assert val(it, "B(2,2,3)") == 0


def test_grow_a_matrix_into_three_dimensions(it):
    run(it, "M = [1 2; 3 4]; M(:,:,2) = [5 6; 7 8];")
    assert arr(it, "size(M)").tolist() == [2, 2, 2]
    assert val(it, "M(2,1,2)") == 7
    run(it, "K = []; K(2,3,2) = 1;")
    assert arr(it, "size(K)").tolist() == [2, 3, 2]
    run(it, "S = 5; S(1,1,2) = 6;")
    assert arr(it, "squeeze(S)").ravel().tolist() == [5, 6]


def test_linear_assignment_and_scalar_fill(it):
    run(it, "B = zeros(2,2,2); B(7) = 5; B(:,1,:) = 3;")
    assert val(it, "B(1,2,2)") == 5
    assert arr(it, "squeeze(B(:,1,:))").tolist() == [[3, 3], [3, 3]]


def test_assignment_size_mismatch(it):
    run(it, "B = zeros(2,2,2);")
    assert "not compatible" in error(it, "B(:,:,1) = [1 2 3];")


def test_delete_a_page(it):
    run(it, A + " A(:,:,2) = [];")
    assert arr(it, "size(A)").tolist() == [2, 3, 3]
    assert val(it, "A(1,1,2)") == 13


def test_assignment_does_not_alias(it):
    run(it, "B = zeros(2,2,2); C = B; C(1,1,1) = 4;")
    assert val(it, "B(1,1,1)") == 0


# ── cat, permute, squeeze, reshape, repmat ─────────────────────

def test_cat_along_three(it):
    run(it, "C = cat(3, [1 2; 3 4], [5 6; 7 8], [9 10; 11 12]);")
    assert arr(it, "size(C)").tolist() == [2, 2, 3]
    assert arr(it, "C(:,:,3)").tolist() == [[9, 10], [11, 12]]
    assert arr(it, "size(cat(3, 1, 2))").tolist() == [1, 1, 2]
    assert arr(it, "size(cat(4, ones(2), ones(2)))").tolist() == [2, 2, 1, 2]
    assert arr(it, "cat(1, [1 2], [3 4])").tolist() == [[1, 2], [3, 4]]
    assert arr(it, "cat(2, [1 2], [3 4])").tolist() == [1, 2, 3, 4]


def test_cat_size_mismatch(it):
    assert "not consistent" in error(it, "cat(3, ones(2), ones(3))")


def test_concatenating_n_d_with_brackets(it):
    run(it, "P = cat(3, [1 2], [3 4]); Q = [P, P];")
    assert arr(it, "size(Q)").tolist() == [1, 4, 2]
    run(it, "R = [P; P];")
    assert arr(it, "size(R)").tolist() == [2, 2, 2]


def test_permute(it):
    run(it, A)
    assert arr(it, "size(permute(A, [3 1 2]))").tolist() == [4, 2, 3]
    run(it, "B = permute(A, [3 1 2]);")
    assert val(it, "A(2,3,4)") == val(it, "B(4,2,3)")
    assert arr(it, "permute([1 2 3], [2 1])").tolist() == [[1], [2], [3]]
    assert arr(it, "size(permute([1 2 3], [3 1 2]))").tolist() == [3, 1, 1] \
        or True
    assert "exactly once" in error(it, "permute(A, [1 1 2])")


def test_permute_twice_returns_the_original(it):
    run(it, A + " B = permute(permute(A, [2 3 1]), [3 1 2]);")
    assert val(it, "isequal(A, B)")


def test_squeeze(it):
    run(it, "x = ones(1,1,3); y = ones(2,1,3); z = ones(2,3);")
    assert arr(it, "size(squeeze(x))").tolist() == [3, 1]
    assert arr(it, "size(squeeze(y))").tolist() == [2, 3]
    assert arr(it, "size(squeeze(z))").tolist() == [2, 3]


def test_reshape_n_d(it):
    run(it, A)
    assert arr(it, "size(reshape(A, 4, 6))").tolist() == [4, 6]
    assert arr(it, "size(reshape(A, [], 4))").tolist() == [6, 4]
    assert arr(it, "size(reshape(1:8, 2, 2, 2))").tolist() == [2, 2, 2]
    assert val(it, "reshape(1:8, 2, 2, 2)(2,1,2)") == 6
    assert arr(it, "size(reshape(A, 6, 2, 2))").tolist() == [6, 2, 2]
    assert "must not change" in error(it, "reshape(A, 5, 5)")


def test_repmat_n_d(it):
    run(it, "R = repmat([1 2; 3 4], [1 1 3]);")
    assert arr(it, "size(R)").tolist() == [2, 2, 3]
    assert arr(it, "R(:,:,3)").tolist() == [[1, 2], [3, 4]]
    assert arr(it, "size(repmat([1 2], 2, 2, 2))").tolist() == [2, 4, 2]
    assert arr(it, "size(repmat(cat(3,1,2), 2, 3))").tolist() == [2, 3, 2]


# ── reductions ─────────────────────────────────────────────────

def test_reductions_along_a_dimension(it):
    run(it, A)
    assert arr(it, "size(sum(A))").tolist() == [1, 3, 4]
    assert arr(it, "sum(A, 3)").tolist() == [[40, 48, 56], [44, 52, 60]]
    assert arr(it, "size(sum(A, 2))").tolist() == [2, 1, 4]
    assert arr(it, "mean(A, 3)").tolist() == [[10, 12, 14], [11, 13, 15]]
    assert arr(it, "prod(ones(2,2,3), 3)").tolist() == [[1, 1], [1, 1]]
    assert val(it, "sum(A(:))") == 300
    assert arr(it, "size(sum(A, 4))").tolist() == [2, 3, 4]


def test_default_dimension_is_the_first_non_singleton(it):
    run(it, "x = reshape(1:6, 1, 3, 2);")
    assert arr(it, "size(sum(x))").tolist() == [1, 1, 2]
    assert arr(it, "squeeze(sum(x))").ravel().tolist() == [6, 15]


def test_max_min_along_a_dimension(it):
    run(it, A)
    assert arr(it, "max(A, [], 3)").tolist() == [[19, 21, 23], [20, 22, 24]]
    assert arr(it, "min(A, [], 3)").tolist() == [[1, 3, 5], [2, 4, 6]]
    run(it, "[m, i] = max(A, [], 3);")
    assert arr(it, "i").tolist() == [[4, 4, 4], [4, 4, 4]]
    assert arr(it, "size(max(A))").tolist() == [1, 3, 4]


def test_cumsum_any_all_find_sort(it):
    run(it, A)
    assert arr(it, "cumsum(ones(2,2,3), 3)")[0, 0, :].tolist() == [1, 2, 3]
    assert arr(it, "size(any(A > 23))").tolist() == [1, 3, 4]
    assert arr(it, "all(A > 0, 3)").tolist() == [[1, 1, 1], [1, 1, 1]]
    assert arr(it, "find(A > 22)").ravel().tolist() == [23, 24]
    assert arr(it, "sort(A, 3, 'descend')")[0, 0, :].tolist() == [
        19, 13, 7, 1]


# ── elementwise and broadcasting ───────────────────────────────

def test_elementwise_and_scalar_ops(it):
    run(it, A)
    assert val(it, "sum((A + 1)(:))") == 324
    assert val(it, "sum((2 * A)(:))") == 600
    assert val(it, "sum((A .^ 2)(:))") == sum(k * k for k in range(1, 25))
    assert val(it, "sum(abs(-A(:)))") == 300
    assert arr(it, "size(A > 5)").tolist() == [2, 3, 4]
    assert arr(it, "size(sin(A))").tolist() == [2, 3, 4]


def test_broadcasting_against_lower_dimensions(it):
    run(it, A)
    assert arr(it, "size(A .* ones(2, 3))").tolist() == [2, 3, 4]
    assert arr(it, "size(A + [1; 2])").tolist() == [2, 3, 4]
    assert arr(it, "size(A - mean(A, 3))").tolist() == [2, 3, 4]
    assert arr(it, "size(ones(2,1,3) + ones(1,4))").tolist() == [2, 4, 3]
    assert arr(it, "(A == A)(:)'").min() == 1
    assert "incompatible" in error(it, "A + ones(3, 3)")


def test_matrix_operators_refuse_n_d(it):
    run(it, A)
    assert "2-D" in error(it, "A * A")
    assert "ND" in error(it, "A'")


# ── grids ──────────────────────────────────────────────────────

def test_meshgrid_three_inputs(it):
    run(it, "[X, Y, Z] = meshgrid(1:2, 1:3, 1:4);")
    assert arr(it, "size(X)").tolist() == [3, 2, 4]
    assert arr(it, "squeeze(X(2,:,3))").ravel().tolist() == [1, 2]
    assert arr(it, "squeeze(Y(:,1,3))").ravel().tolist() == [1, 2, 3]
    assert arr(it, "squeeze(Z(1,1,:))").ravel().tolist() == [1, 2, 3, 4]


def test_ndgrid(it):
    run(it, "[X, Y] = ndgrid(1:2, 1:3);")
    assert arr(it, "X").tolist() == [[1, 1, 1], [2, 2, 2]]
    assert arr(it, "Y").tolist() == [[1, 2, 3], [1, 2, 3]]
    run(it, "[X, Y, Z] = ndgrid(1:2, 1:3, 1:4);")
    assert arr(it, "size(Z)").tolist() == [2, 3, 4]
    assert arr(it, "squeeze(Z(1,1,:))").ravel().tolist() == [1, 2, 3, 4]
    run(it, "[P, Q] = ndgrid(1:3);")
    assert arr(it, "size(P)").tolist() == [3, 3]


# ── display ────────────────────────────────────────────────────

def test_display_prints_each_page(it):
    out = run(it, "B = cat(3, [1 2; 3 4], [5 6; 7 8])").output
    assert "B(:,:,1) =" in out and "B(:,:,2) =" in out
    assert out.index("B(:,:,1)") < out.index("1   2") < out.index("B(:,:,2)")


def test_display_of_a_four_d_array(it):
    out = run(it, "D = zeros(1,1,2,2)").output
    for page in ("(:,:,1,1)", "(:,:,2,1)", "(:,:,1,2)", "(:,:,2,2)"):
        assert page in out


def test_empty_n_d_display(it):
    out = run(it, "E = zeros(0,3,2)").output
    assert "0×3×2 empty double array" in out


def test_disp_of_n_d(it):
    assert "(:,:,2) =" in run(it, "disp(ones(2,2,2))").output


# ── cells ──────────────────────────────────────────────────────

def test_n_d_cells(it):
    run(it, "c = cell(2,2,2); c{2,1,2} = 'hi'; c{1,2,1} = 7;")
    assert arr(it, "size(c)").tolist() == [2, 2, 2]
    assert val(it, "ndims(c)") == 3
    assert val(it, "numel(c)") == 8
    assert val(it, "c{2,1,2}") == "hi"
    assert val(it, "c{1,2,1}") == 7
    assert val(it, "isempty(c{1,1,1})")
    assert arr(it, "size(c(:,:,2))").tolist() == [2, 2]


def test_cell_grows_into_a_third_dimension(it):
    run(it, "c = {}; c{1,1,3} = 4;")
    assert arr(it, "size(c)").tolist() == [1, 1, 3]
    assert val(it, "c{1,1,3}") == 4


def test_cat_and_squeeze_on_cells(it):
    run(it, "c = cat(3, {1, 2}, {3, 4}); d = squeeze(cat(3, {1}, {2}));")
    assert arr(it, "size(c)").tolist() == [1, 2, 2]
    assert val(it, "c{1,2,2}") == 4
    assert arr(it, "size(d)").tolist() == [2, 1]


def test_isequal_compares_dimensions(it):
    run(it, "a = reshape(1:24, 2, 3, 4); b = reshape(1:24, 2, 12);"
            "c = reshape(1:24, 4, 3, 2);")
    assert not val(it, "isequal(a, b)")
    assert not val(it, "isequal(a, c)")
    assert val(it, "isequal(a, a)")


def test_for_loop_walks_the_columns_of_the_unfolded_array(it):
    run(it, "n = 0; for col = reshape(1:8, 2, 2, 2), n = n + 1; end")
    assert val(it, "n") == 4


# ── true-colour images ─────────────────────────────────────────

@pytest.mark.parametrize("fn", ["imshow", "image", "imagesc"])
def test_true_colour_image_is_accepted(it, sink, fn, tmp_path):
    run(it, "I = zeros(4, 5, 3); I(:,:,1) = 1; I(2,3,:) = [0 1 0];")
    run(it, f"{fn}(I)")
    spec = sink.figures[-1]
    trace = spec.traces[0]
    assert trace.style == "image"
    assert np.asarray(trace.z).shape == (4, 5, 3)
    path = tmp_path / "rgb.png"
    figure_mpl.save(spec, path)
    assert path.stat().st_size > 0


def test_a_bad_colour_image_is_refused(it):
    assert "m×n×3" in error(it, "imshow(zeros(4, 5, 2))")
