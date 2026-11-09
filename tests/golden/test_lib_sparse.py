"""
Sparse matrices: sparse, speye, spalloc, spdiags, nnz, full, the operators on
them, pcg, gmres, bicgstab and eigs.

Each test types the command the way a user would and checks it against values
worked out by hand from MATLAB's documented behaviour, never against what
Evans printed.
"""

from __future__ import annotations

import numpy as np
import pytest

from evans.console import Interpreter, set_figure_sink
from evans.console import matlab_runtime as _mr  # noqa: F401  (installs sparse)
from evans.console.figures import recording_sink
from evans.console.lib_sparse import Sparse
from evans.console.matlab_runtime import Cell


@pytest.fixture
def it():
    previous = set_figure_sink(recording_sink())
    yield Interpreter()
    set_figure_sink(previous)


def run(it, source: str):
    results = it.run_script(source, "matlab")
    failed = [r for r in results if r.error]
    assert not failed, f"{failed[0].source!r} → {failed[0].error}"
    return results


def error_of(it, source: str) -> str:
    results = it.run_script(source, "matlab")
    failed = [r for r in results if r.error]
    assert failed, f"{source!r} should have failed"
    return failed[0].error


def value(it, name: str):
    return it.namespace[name]


def full(it, name: str) -> np.ndarray:
    return np.asarray(value(it, name).m.toarray())


# ── construction ──────────────────────────────────────────────────

def test_sparse_from_triplets_adds_duplicates(it):
    run(it, "S = sparse([1 2 2], [1 2 2], [4 5 6], 3, 3);")
    assert isinstance(value(it, "S"), Sparse)
    assert full(it, "S").tolist() == [[4, 0, 0], [0, 11, 0], [0, 0, 0]]


def test_sparse_infers_the_size_from_the_largest_subscripts(it):
    run(it, "S = sparse([1 3], [2 4], [1 1]); n = size(S);")
    assert value(it, "n").tolist() == [3, 4]


def test_sparse_of_a_full_matrix_and_back(it):
    run(it, "A = [1 0; 0 2]; S = sparse(A); B = full(S); c = nnz(S);")
    assert value(it, "c") == 2
    assert np.array_equal(value(it, "B"), [[1, 0], [0, 2]])


def test_sparse_m_n_is_all_zeros_and_speye_is_the_identity(it):
    run(it, "Z = sparse(2, 3); I = speye(3); J = speye(2, 3); "
            "z = nnz(Z); i = nnz(I);")
    assert value(it, "z") == 0 and value(it, "i") == 3
    assert full(it, "J").tolist() == [[1, 0, 0], [0, 1, 0]]


def test_spalloc_spones_and_nzmax(it):
    run(it, "S = spalloc(3, 3, 5); S(2, 2) = 7; O = spones(S); "
            "o = full(O); n = nzmax(S);")
    assert value(it, "o").tolist() == [[0, 0, 0], [0, 1, 0], [0, 0, 0]]
    assert value(it, "n") == 1


def test_sprand_has_the_asked_density(it):
    run(it, "rng(3); R = sprand(10, 10, 0.2); n = nnz(R); s = issparse(R);")
    assert value(it, "n") == 20
    assert value(it, "s") is True or value(it, "s") == 1


def test_issparse(it):
    run(it, "a = issparse(speye(2)); b = issparse(eye(2)); "
            "c = issparse(speye(2) * ones(2));")
    assert (value(it, "a"), value(it, "b"), value(it, "c")) == (
        True, False, False)


def test_a_bad_subscript_is_refused(it):
    assert "Subscripts" in error_of(it, "sparse([0 1], [1 1], [1 1]);")
    assert "same length" in error_of(it, "sparse([1 2], [1 2 3], [1 2]);")


# ── operators ─────────────────────────────────────────────────────

def test_sum_difference_and_scaling_stay_sparse(it):
    run(it, "A = sparse([1 2], [1 2], [1 2]); B = speye(2); "
            "C = A + B; D = A - B; E = 3 * A; F = A .* 2; G = A / 2; "
            "H = -A; T = A';")
    for name in "CDEFGHT":
        assert isinstance(value(it, name), Sparse), name
    assert full(it, "C").tolist() == [[2, 0], [0, 3]]
    assert full(it, "D").tolist() == [[0, 0], [0, 1]]
    assert full(it, "E").tolist() == [[3, 0], [0, 6]]
    assert full(it, "G").tolist() == [[0.5, 0], [0, 1]]


def test_sparse_plus_scalar_is_full(it):
    run(it, "A = sparse([1 0; 0 2]) + 1;")
    assert not isinstance(value(it, "A"), Sparse)
    assert np.array_equal(value(it, "A"), [[2, 1], [1, 3]])


def test_sparse_times_full_is_full_and_times_sparse_is_sparse(it):
    run(it, "A = sparse([1 2; 0 3]); x = A * [1; 1]; B = A * A; "
            "y = [1 1] * A;")
    assert np.array_equal(np.asarray(value(it, "x")).reshape(-1), [3, 3])
    assert isinstance(value(it, "B"), Sparse)
    assert full(it, "B").tolist() == [[1, 8], [0, 9]]
    assert np.array_equal(np.asarray(value(it, "y")).reshape(-1), [1, 5])


def test_elementwise_product_of_sparse_and_full_stays_sparse(it):
    run(it, "A = sparse([1 0; 0 2]); B = A .* [5 5; 5 5];")
    assert isinstance(value(it, "B"), Sparse)
    assert full(it, "B").tolist() == [[5, 0], [0, 10]]


def test_incompatible_sizes_are_reported(it):
    assert "Incorrect dimensions" in error_of(
        it, "A = speye(2) * ones(3, 1);")
    assert "incompatible sizes" in error_of(it, "A = speye(2) + speye(3);")


def test_backslash_solves_a_sparse_system(it):
    # [2 1; 1 3] x = [3; 5]  ->  x = [0.8; 1.4]
    run(it, "A = sparse([2 1; 1 3]); x = A \\ [3; 5];")
    assert np.allclose(np.asarray(value(it, "x")).reshape(-1), [0.8, 1.4])
    assert not isinstance(value(it, "x"), Sparse)


def test_backslash_with_several_right_hand_sides(it):
    run(it, "A = sparse([2 0; 0 4]); X = A \\ [2 4; 4 8];")
    assert np.allclose(value(it, "X"), [[1, 2], [1, 2]])


def test_a_singular_sparse_system_is_an_error(it):
    assert "singular" in error_of(it, "A = sparse([1 1; 1 1]); A \\ [1; 2];")


def test_right_division_by_a_sparse_matrix(it):
    # b / A solves x*A = b
    run(it, "A = sparse([2 0; 0 4]); x = [2 4] / A;")
    assert np.allclose(value(it, "x"), [1, 1])


def test_matrix_power(it):
    run(it, "A = sparse([1 1; 0 1]); B = A ^ 3;")
    assert full(it, "B").tolist() == [[1, 3], [0, 1]]


def test_comparison_with_a_scalar_keeps_the_pattern(it):
    run(it, "A = sparse([1 0; 0 5]); B = A > 2; C = A == 0;")
    assert isinstance(value(it, "B"), Sparse)
    assert full(it, "B").tolist() == [[False, False], [False, True]]
    assert not isinstance(value(it, "C"), Sparse)     # zeros become true
    assert np.array_equal(value(it, "C"), [[False, True], [True, False]])


def test_if_on_a_sparse_matrix_needs_every_element_nonzero(it):
    run(it, "A = sparse([1 1; 1 0]); if A, r = 1; else, r = 2; end")
    assert value(it, "r") == 2


# ── indexing, assignment, concatenation ───────────────────────────

def test_indexing_by_rows_columns_and_linear_index(it):
    run(it, "A = sparse([1 2 3; 4 5 6; 7 8 9]); r = A(2, :); c = A(:, 3); "
            "e = A(end, end); L = A([1 5 9]); b = A(2:3, 2:3);")
    assert isinstance(value(it, "r"), Sparse)
    assert full(it, "r").tolist() == [[4, 5, 6]]
    assert full(it, "c").tolist() == [[3], [6], [9]]
    assert value(it, "e") == 9
    assert full(it, "L").tolist() == [[1, 5, 9]]
    assert full(it, "b").tolist() == [[5, 6], [8, 9]]


def test_a_linear_index_of_a_column_vector_stays_a_column(it):
    run(it, "v = sparse([1; 0; 3]); w = v([1 3]);")
    assert full(it, "w").tolist() == [[1], [3]]


def test_colon_makes_a_column_in_matlab_order(it):
    run(it, "A = sparse([1 2; 3 4]); v = A(:);")
    assert full(it, "v").reshape(-1).tolist() == [1, 3, 2, 4]


def test_assignment_grows_and_overwrites(it):
    run(it, "A = sparse(2, 2); A(1, 2) = 3; A(3, 3) = 4; A(1, 2) = 0; "
            "n = nnz(A); s = size(A);")
    assert value(it, "s").tolist() == [3, 3]
    assert value(it, "n") == 1


def test_assigning_a_row_and_deleting_a_column(it):
    run(it, "A = sparse(3, 3); A(2, :) = [1 2 3]; A(:, 1) = []; s = size(A);")
    assert value(it, "s").tolist() == [3, 2]
    assert full(it, "A").tolist() == [[0, 0], [2, 3], [0, 0]]


def test_assignment_with_the_wrong_size_is_refused(it):
    assert "Unable to perform assignment" in error_of(
        it, "A = sparse(3, 3); A(1:2, 1) = [1 2 3];")


def test_concatenation_stays_sparse(it):
    run(it, "A = speye(2); B = [A, 2*A; zeros(2), A]; s = size(B);")
    assert isinstance(value(it, "B"), Sparse)
    assert value(it, "s").tolist() == [4, 4]
    assert full(it, "B")[0].tolist() == [1, 0, 2, 0]


# ── functions that know about sparse ─────────────────────────────

def test_size_class_and_friends_do_not_densify(it):
    run(it, "A = sparse(100000, 100000); n = size(A, 1); c = class(A); "
            "e = isempty(A); m = numel(A) > 1e9;")
    assert value(it, "n") == 100000
    assert value(it, "c") == "double"
    assert value(it, "e") in (False, 0)


def test_a_logical_sparse_matrix_is_logical(it):
    run(it, "A = sparse([1 0; 0 5]) > 2; c = class(A);")
    assert value(it, "c") == "logical"


def test_sum_abs_diag_trace_norm(it):
    run(it, "A = sparse([1 -2; 0 3]); s = full(sum(A)); t = full(sum(A, 2)); "
            "a = full(abs(A)); d = full(diag(A)); tr = trace(A); "
            "n1 = norm(A, 1); ni = norm(A, inf); nf = norm(A, 'fro');")
    assert value(it, "s").tolist() == [1, 1]
    assert np.array_equal(np.asarray(value(it, "t")).reshape(-1), [-1, 3])
    assert value(it, "a").tolist() == [[1, 2], [0, 3]]
    assert np.array_equal(np.asarray(value(it, "d")).reshape(-1), [1, 3])
    assert value(it, "tr") == 4
    assert value(it, "n1") == 5 and value(it, "ni") == 3
    assert value(it, "nf") == pytest.approx(np.sqrt(14))


def test_find_with_three_outputs_lists_column_by_column(it):
    run(it, "A = sparse([0 2; 3 0]); [i, j, v] = find(A);")
    for name, want in (("i", [2, 1]), ("j", [1, 2]), ("v", [3, 2])):
        assert np.asarray(value(it, name)).reshape(-1).tolist() == want


def test_nonzeros_and_nnz_ignore_stored_zeros(it):
    run(it, "A = sparse([1 2 2], [1 1 2], [4 5 6]); v = nonzeros(A); "
            "n = nnz(sparse([1 2], [1 2], [0 7]));")
    assert np.asarray(value(it, "v")).reshape(-1).tolist() == [4, 5, 6]
    assert value(it, "n") == 1
    run(it, "m = nnz([1 0 2; 0 0 3]);")
    assert value(it, "m") == 3


def test_other_functions_get_the_full_matrix(it):
    run(it, "A = sparse([4 0; 0 9]); r = sqrt(A); t = det(A);")
    assert not isinstance(value(it, "r"), Sparse)
    assert np.allclose(value(it, "r"), [[2, 0], [0, 3]])
    assert value(it, "t") == pytest.approx(36)


def test_spfun_touches_only_the_stored_entries(it):
    run(it, "A = sparse([1 2], [1 2], [0 1]); B = spfun(@exp, A); "
            "b = full(B);")
    assert np.allclose(value(it, "b"), [[0, 0], [0, np.e]])


def test_kron_tril_triu(it):
    run(it, "A = sparse([1 2; 3 4]); K = kron(speye(2), A); L = full(tril(A)); "
            "U = full(triu(A));")
    assert isinstance(value(it, "K"), Sparse)
    assert full(it, "K").shape == (4, 4)
    assert value(it, "L").tolist() == [[1, 0], [3, 4]]
    assert value(it, "U").tolist() == [[1, 2], [0, 4]]


# ── spdiags ───────────────────────────────────────────────────────

def test_spdiags_builds_the_matlab_documentation_example(it):
    # B columns are the diagonals -1, 0, 1 of a 3x3 matrix; each entry lines
    # up with its column, so A(2,1)=B(1,1), A(1,2)=B(2,3), A(3,3)=B(3,2).
    run(it, "A = spdiags([1 2 3; 4 5 6; 7 8 9], [-1 0 1], 3, 3);")
    assert full(it, "A").tolist() == [[2, 6, 0], [1, 5, 9], [0, 4, 8]]


def test_spdiags_extracts_diagonals(it):
    run(it, "A = sparse([1 2 0; 3 4 5; 0 6 7]); [B, d] = spdiags(A); "
            "m = spdiags(A, 0);")
    assert np.asarray(value(it, "d")).reshape(-1).tolist() == [-1, 0, 1]
    assert np.asarray(value(it, "m")).reshape(-1).tolist() == [1, 4, 7]
    assert value(it, "B").tolist() == [[3, 1, 0], [6, 4, 2], [0, 7, 5]]


def test_spdiags_on_a_wide_matrix_lines_up_with_the_row(it):
    run(it, "A = spdiags([1 2]', 1, 2, 3);")
    assert full(it, "A").tolist() == [[0, 1, 0], [0, 0, 2]]


def test_spdiags_replaces_a_diagonal(it):
    run(it, "A = spdiags([9 9 9]', 0, speye(3));")
    assert full(it, "A").tolist() == [[9, 0, 0], [0, 9, 0], [0, 0, 9]]


# ── iterative solvers ─────────────────────────────────────────────

LAPLACE = ("n = 40; e = ones(n, 1); "
           "K = spdiags([-e 2*e -e], -1:1, n, n); b = K * e;")


def test_pcg_solves_the_laplacian(it):
    run(it, LAPLACE + "[x, flag, relres, iter, resvec] = pcg(K, b, 1e-10, "
                      "200);")
    assert value(it, "flag") == 0
    assert np.allclose(value(it, "x"), 1.0, atol=1e-6)
    assert value(it, "relres") <= 1e-10
    # CG on a tridiagonal system with 40 unknowns needs at most 40 steps
    assert 1 <= value(it, "iter") <= 40
    assert len(np.asarray(value(it, "resvec")).reshape(-1)) == \
        value(it, "iter") + 1


def test_pcg_reports_when_it_runs_out_of_iterations(it):
    run(it, LAPLACE + "[x, flag] = pcg(K, b, 1e-12, 3);")
    assert value(it, "flag") == 1


def test_pcg_without_a_flag_output_says_how_it_ended(it):
    results = run(it, LAPLACE + "x = pcg(K, b, 1e-10, 200);")
    assert "pcg converged at iteration" in results[-1].display()


def test_pcg_with_a_preconditioner(it):
    run(it, LAPLACE + "M = spdiags(2*e, 0, n, n); "
                      "[x, flag] = pcg(K, b, 1e-10, 200, M);")
    assert value(it, "flag") == 0
    assert np.allclose(value(it, "x"), 1.0, atol=1e-6)


def test_gmres_and_its_iteration_pair(it):
    run(it, "A = sparse([4 1 0; 1 3 1; 0 1 2]); b = [1; 2; 3]; "
            "[x, flag, relres, iter] = gmres(A, b, [], 1e-12, 3);")
    assert value(it, "flag") == 0
    assert np.allclose(np.asarray(value(it, "x")).reshape(-1),
                       np.linalg.solve([[4, 1, 0], [1, 3, 1], [0, 1, 2]],
                                       [1, 2, 3]))
    assert np.asarray(value(it, "iter")).reshape(-1).tolist()[0] == 1


@pytest.mark.parametrize("name", ["bicgstab", "bicg"])
def test_bicg_family_on_a_nonsymmetric_system(it, name):
    run(it, "A = sparse([4 1 0; 2 3 1; 0 1 2]); b = [1; 2; 3]; "
            f"[x, flag] = {name}(A, b, 1e-10, 50);")
    assert value(it, "flag") == 0
    assert np.allclose(np.asarray(value(it, "x")).reshape(-1),
                       np.linalg.solve([[4, 1, 0], [2, 3, 1], [0, 1, 2]],
                                       [1, 2, 3]), atol=1e-7)


def test_minres_on_a_symmetric_indefinite_system(it):
    run(it, "A = sparse([2 1 0; 1 -3 1; 0 1 2]); b = [1; 0; 1]; "
            "[x, flag] = minres(A, b, 1e-10, 50);")
    assert value(it, "flag") == 0
    assert np.allclose(np.asarray(value(it, "x")).reshape(-1),
                       np.linalg.solve([[2, 1, 0], [1, -3, 1], [0, 1, 2]],
                                       [1, 0, 1]), atol=1e-7)


def test_a_zero_right_hand_side_gives_zero(it):
    run(it, "A = speye(3); [x, flag] = pcg(A, zeros(3, 1));")
    assert value(it, "flag") == 0
    assert np.allclose(value(it, "x"), 0)


def test_solver_argument_errors(it):
    assert "square" in error_of(it, "pcg(sparse(2, 3), [1; 2]);")
    assert "rows" in error_of(it, "pcg(speye(3), [1; 2]);")


# ── eigs ──────────────────────────────────────────────────────────

def test_eigs_largest_of_the_laplacian(it):
    # eigenvalues of tridiag(-1,2,-1), n=60:  2 - 2 cos(k pi/61)
    run(it, "n = 60; e = ones(n, 1); K = spdiags([-e 2*e -e], -1:1, n, n); "
            "d = eigs(K, 3);")
    k = np.arange(60, 57, -1)
    expected = 2 - 2 * np.cos(k * np.pi / 61)
    assert np.allclose(np.asarray(value(it, "d")).reshape(-1), expected,
                       atol=1e-8)


def test_eigs_smallest_and_near_a_shift(it):
    run(it, "n = 60; e = ones(n, 1); K = spdiags([-e 2*e -e], -1:1, n, n); "
            "s = eigs(K, 2, 'smallestabs'); t = eigs(K, 1, 1.0);")
    k = np.array([1, 2])
    assert np.allclose(np.asarray(value(it, "s")).reshape(-1),
                       2 - 2 * np.cos(k * np.pi / 61), atol=1e-8)
    all_ev = 2 - 2 * np.cos(np.arange(1, 61) * np.pi / 61)
    near = all_ev[np.argmin(abs(all_ev - 1.0))]
    assert np.asarray(value(it, "t")).reshape(-1)[0] == pytest.approx(near)


def test_eigs_returns_vectors_and_a_diagonal_matrix(it):
    run(it, "n = 60; e = ones(n, 1); K = spdiags([-e 2*e -e], -1:1, n, n); "
            "[V, D] = eigs(K, 2); r = norm(K * V - V * D) < 1e-7; "
            "s = size(V);")
    assert value(it, "s").tolist() == [60, 2]
    assert value(it, "r")


def test_eigs_on_a_small_matrix_is_exact(it):
    run(it, "d = eigs(sparse([2 0 0; 0 5 0; 0 0 1]), 2);")
    assert np.asarray(value(it, "d")).reshape(-1).tolist() == [5, 2]


def test_svds_gives_the_largest_singular_values(it):
    run(it, "s = svds(sparse(diag(1:8)), 3);")
    assert np.allclose(np.asarray(value(it, "s")).reshape(-1), [8, 7, 6])


# ── interaction with the rest ─────────────────────────────────────

def test_a_sparse_matrix_survives_save_and_load(it, tmp_path):
    path = (tmp_path / "s.mat").as_posix()
    run(it, f"S = sparse([1 3], [2 3], [5 6]); save('{path}', 'S'); "
            f"clear S; load('{path}'); ok = issparse(S); n = nnz(S);")
    assert value(it, "ok") and value(it, "n") == 2


def test_a_sparse_variable_is_listed_and_displayed(it):
    results = run(it, "S = sparse([1 2], [1 2], [3 4])\nwhos")
    shown = results[0].display()
    assert "(1,1)" in shown and "(2,2)" in shown
    assert "S" in results[1].display()


def test_an_all_zero_sparse_matrix_says_so(it):
    results = run(it, "Z = sparse(3, 3)")
    assert "All zero sparse: 3-by-3" in results[0].display()


def test_cells_can_hold_a_sparse_matrix(it):
    run(it, "c = {speye(2), 1}; b = issparse(c{1});")
    assert isinstance(value(it, "c"), Cell) and value(it, "b")
