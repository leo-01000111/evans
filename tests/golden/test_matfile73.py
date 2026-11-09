"""
.mat files of version 7.3 (HDF5): ``save -v7.3`` and ``load``, with the
version 5 path left as it was.

There is no MATLAB here to write a reference file, so the layout is checked
against the documented format directly: the header, the reversed dimensions,
the ``MATLAB_class`` tags, ``#refs#`` for cells.
"""

from __future__ import annotations

import numpy as np
import pytest

h5py = pytest.importorskip("h5py")

from evans.console import (
    Interpreter,  # noqa: E402
    matfile73,  # noqa: E402
)
from evans.console.matlab_runtime import Cell, Struct, StructArray  # noqa: E402


@pytest.fixture
def it():
    return Interpreter()


def run(it, source: str):
    results = it.run_script(source, "matlab")
    failed = [r for r in results if r.error]
    assert not failed, f"{failed[0].source!r} → {failed[0].error}"
    return results


def value(it, name: str):
    return it.namespace[name]


def roundtrip(it, tmp_path, setup: str):
    path = (tmp_path / "v.mat").as_posix()
    run(it, f"{setup}\nsave('{path}', '-v7.3');")
    other = Interpreter()
    run(other, f"load('{path}');")
    return other, path


def test_the_file_is_hdf5_with_matlabs_header(it, tmp_path):
    _, path = roundtrip(it, tmp_path, "a = [1 2; 3 4];")
    raw = open(path, "rb").read(512)
    assert raw.startswith(b"MATLAB 7.3 MAT-file")
    assert raw[124:128] == b"\x00\x02IM"             # version 0x0200, 'IM'
    assert matfile73.is_v73(path)
    with h5py.File(path, "r") as f:
        assert f["a"].attrs["MATLAB_class"] == b"double"
        # column-major data under reversed dimensions: the 2x2 [1 2; 3 4]
        # is stored as [[1, 3], [2, 4]]
        assert f["a"][()].tolist() == [[1, 3], [2, 4]]


def test_a_non_square_matrix_is_stored_with_reversed_dimensions(it, tmp_path):
    _, path = roundtrip(it, tmp_path, "a = [1 2 3; 4 5 6];")
    with h5py.File(path, "r") as f:
        assert f["a"].shape == (3, 2)


def test_numbers_vectors_and_matrices_round_trip(it, tmp_path):
    other, _ = roundtrip(
        it, tmp_path, "a = [1 2; 3 4]; s = 5; r = 1:4; c = [1;2;3]; "
                      "x = 2.5; e = [];")
    assert value(other, "a").tolist() == [[1, 2], [3, 4]]
    assert value(other, "s") == 5
    assert value(other, "r").tolist() == [1, 2, 3, 4]
    assert value(other, "c").tolist() == [[1], [2], [3]]
    assert value(other, "x") == 2.5
    assert np.size(value(other, "e")) == 0


def test_text_logicals_and_complex_numbers(it, tmp_path):
    other, path = roundtrip(
        it, tmp_path, "t = 'hello world'; l = true; z = 3+4i; "
                      "za = [1+2i 3-1i]; m = [true false true]; em = '';")
    assert value(other, "t") == "hello world"
    assert bool(value(other, "l")) is True
    assert value(other, "z") == 3 + 4j
    assert value(other, "za").tolist() == [1 + 2j, 3 - 1j]
    assert value(other, "m").dtype == bool
    assert value(other, "em") == ""
    with h5py.File(path, "r") as f:
        assert f["t"].attrs["MATLAB_class"] == b"char"
        assert f["t"].dtype == np.dtype("<u2")
        assert f["l"].attrs["MATLAB_class"] == b"logical"


def test_cells_use_references_into_refs(it, tmp_path):
    other, path = roundtrip(
        it, tmp_path, "c = {1, 'two', [3 4 5]; {6}, 7, 8};")
    c = value(other, "c")
    assert isinstance(c, Cell) and c.dims == (2, 3)
    assert c[0] == 1 and c[2] == "two" and c[4].tolist() == [3, 4, 5]
    assert isinstance(c[1], Cell) and c[1][0] == 6
    with h5py.File(path, "r") as f:
        assert f["c"].attrs["MATLAB_class"] == b"cell"
        assert "#refs#" in f


def test_structs_keep_their_field_order_and_nesting(it, tmp_path):
    other, path = roundtrip(
        it, tmp_path, "s.zeta = 1; s.alpha = 'a'; s.inner.v = [1;2]; "
                      "s.list = {1, 2};")
    s = value(other, "s")
    assert isinstance(s, Struct)
    assert list(s) == ["zeta", "alpha", "inner", "list"]
    assert s["inner"]["v"].tolist() == [[1], [2]]
    assert list(s["list"]) == [1, 2]
    with h5py.File(path, "r") as f:
        assert f["s"].attrs["MATLAB_class"] == b"struct"


def test_struct_arrays(it, tmp_path):
    other, _ = roundtrip(it, tmp_path, "sa = struct('n', {1, 2, 3}, "
                                       "'t', {'a', 'b', 'c'});")
    sa = value(other, "sa")
    assert isinstance(sa, StructArray) and len(sa) == 3
    assert [e["n"] for e in sa] == [1, 2, 3]
    assert [e["t"] for e in sa] == ["a", "b", "c"]


def test_sparse_matrices_are_a_group_with_data_ir_jc(it, tmp_path):
    other, path = roundtrip(
        it, tmp_path, "S = sparse([1 3], [2 3], [5 6], 3, 3);")
    S = value(other, "S")
    assert S.m.toarray().tolist() == [[0, 5, 0], [0, 0, 0], [0, 0, 6]]
    with h5py.File(path, "r") as f:
        g = f["S"]
        assert int(g.attrs["MATLAB_sparse"]) == 3
        assert g["data"][()].tolist() == [5, 6]
        assert g["ir"][()].tolist() == [0, 2]            # 0-based rows
        assert g["jc"][()].tolist() == [0, 0, 1, 2]      # column pointers


def test_only_the_named_variables_are_saved_and_load_can_filter(it, tmp_path):
    path = (tmp_path / "n.mat").as_posix()
    run(it, f"a = 1; b = 2; cc = 3; save('{path}', 'a', 'cc', '-v7.3');")
    other = Interpreter()
    run(other, f"load('{path}', 'cc');")
    assert value(other, "cc") == 3 and "a" not in other.namespace


def test_append_adds_to_an_existing_73_file(it, tmp_path):
    path = (tmp_path / "ap.mat").as_posix()
    run(it, f"a = 1; save('{path}', 'a', '-v7.3'); b = 2; "
            f"save('{path}', 'b', '-append');")
    other = Interpreter()
    run(other, f"load('{path}');")
    assert value(other, "a") == 1 and value(other, "b") == 2
    assert matfile73.is_v73(path)


def test_load_with_an_output_returns_a_struct(it, tmp_path):
    path = (tmp_path / "o.mat").as_posix()
    run(it, f"p = 3; save('{path}', '-v7.3'); s = load('{path}');")
    assert value(it, "s")["p"] == 3


def test_version_5_is_still_the_default(it, tmp_path):
    path = (tmp_path / "v5.mat").as_posix()
    run(it, f"a = [1 2 3]; save('{path}', 'a');")
    assert not matfile73.is_v73(path)
    assert open(path, "rb").read(10) == b"MATLAB 5.0"
    other = Interpreter()
    run(other, f"load('{path}');")
    assert value(other, "a").tolist() == [1, 2, 3]


def _stamp(path) -> None:
    with open(path, "r+b") as fh:
        fh.write(b"MATLAB 7.3 MAT-file".ljust(124) + b"\x00\x02IM")


def test_a_file_with_matlab_objects_skips_them_with_a_warning(tmp_path):
    """Hand-built as MATLAB writes a table: a group tagged as an object."""
    path = tmp_path / "t.mat"
    with h5py.File(path, "w", userblock_size=512) as f:
        ds = f.create_dataset("ok", data=np.array([[1.0, 2.0]]))
        ds.attrs.create("MATLAB_class", np.bytes_("double"))
        g = f.create_group("T")
        g.attrs.create("MATLAB_class", np.bytes_("table"))
        g.attrs.create("MATLAB_object_decode", np.int32(3))
    _stamp(path)
    it = Interpreter()
    results = run(it, f"load('{path.as_posix()}');")
    shown = results[0].display()
    assert "'T'" in shown and "table" in shown
    assert "T" not in it.namespace
    assert np.asarray(value(it, "ok")).reshape(-1).tolist() == [1.0, 2.0]


def test_reading_a_file_written_the_way_matlab_does(tmp_path):
    """Built from the format's rules, independent of our own writer."""
    path = tmp_path / "m.mat"
    with h5py.File(path, "w", userblock_size=512) as f:
        a = f.create_dataset("a", data=np.array([[1.0, 4.0], [2.0, 5.0],
                                                 [3.0, 6.0]]))   # 2x3 in MATLAB
        a.attrs.create("MATLAB_class", np.bytes_("double"))
        n = f.create_dataset("n", data=np.array([[7]], dtype="u1"))
        n.attrs.create("MATLAB_class", np.bytes_("uint8"))
        s = f.create_dataset("s", data=np.array([[104], [105]], dtype="<u2"))
        s.attrs.create("MATLAB_class", np.bytes_("char"))
    _stamp(path)
    it = Interpreter()
    run(it, f"load('{path.as_posix()}');")
    assert value(it, "a").tolist() == [[1, 2, 3], [4, 5, 6]]
    assert value(it, "n") == 7
    assert value(it, "s") == "hi"
