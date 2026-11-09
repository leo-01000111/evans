"""
MATLAB ``.mat`` files, version 7.3 (HDF5).
==========================================
``load`` and ``save -v7.3`` for files too big for the version 5 format, or
written by MATLAB with ``-v7.3``. :mod:`scipy.io` cannot read these; h5py can.
The version 5 path (``scipy.io.loadmat`` / ``savemat``) is untouched.

How MATLAB lays a value out in HDF5
-----------------------------------
* The file starts with a 512-byte user block, "MATLAB 7.3 MAT-file, ...".
* Every variable is a dataset or group at the top level, tagged with a
  ``MATLAB_class`` attribute (``double``, ``char``, ``cell``, ``struct``...).
* Arrays are stored column-major as HDF5's row-major with the dimensions
  reversed, so a 2×3 matrix is a 3×2 dataset: reading is ``.T``.
* Text is ``uint16`` character codes; a logical is ``uint8``; a complex array
  is a compound type with ``real`` and ``imag``.
* An empty array is a dataset holding its dimensions, tagged ``MATLAB_empty``.
* A cell is a dataset of object references into the ``#refs#`` group; a
  struct is a group of its fields (a struct array's fields are reference
  arrays); a sparse matrix is a group with ``data``, ``ir`` and ``jc``.

Values MATLAB stores through its object system (tables, function handles,
classes) cannot be read; ``load`` skips those variables and says so.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from .matlab_runtime import (
    Cell,
    MatlabError,
    Struct,
    StructArray,
    _normalise,
)

#: What every version 7.3 file begins with.
SIGNATURE = b"MATLAB 7.3 MAT-file"
_USERBLOCK = 512


class Unsupported(Exception):
    """A variable of a kind this reader does not handle; names its class."""


def is_v73(path: str) -> bool:
    """Whether ``path`` is a version 7.3 (HDF5) MAT-file."""
    try:
        with open(path, "rb") as fh:
            return fh.read(len(SIGNATURE)) == SIGNATURE
    except OSError:
        return False


def _h5py():
    try:
        import h5py
    except ImportError:
        raise MatlabError(
            "MAT-files of version 7.3 need the h5py package, which is not "
            "installed.") from None
    return h5py


# ── reading ───────────────────────────────────────────────────────

def _attr(obj, name: str, default=None):
    if name not in obj.attrs:
        return default
    value = obj.attrs[name]
    if isinstance(value, bytes):
        return value.decode("ascii", "replace")
    if isinstance(value, np.ndarray) and value.dtype.kind == "S":
        return value.tobytes().decode("ascii", "replace")
    return value


def load(path: str) -> tuple[dict[str, Any], list[str]]:
    """Every variable in the file, and a warning per variable skipped."""
    h5py = _h5py()
    values: dict[str, Any] = {}
    skipped: list[str] = []
    try:
        with h5py.File(path, "r") as f:
            for name in f:
                if name.startswith("#"):
                    continue
                try:
                    values[name] = _read(f, f[name])
                except Unsupported as exc:
                    skipped.append(f"Variable '{name}' of class "
                                   f"'{exc}' cannot be loaded and was "
                                   f"skipped.")
    except OSError as exc:
        raise MatlabError(f"Unable to read the version 7.3 MAT-file "
                          f"'{path}' ({exc}).") from None
    return values, skipped


def _read(f, obj):
    h5py = _h5py()
    cls = _attr(obj, "MATLAB_class")
    if isinstance(obj, h5py.Group):
        if "MATLAB_object_decode" in obj.attrs:
            raise Unsupported(cls or "object")
        if "MATLAB_sparse" in obj.attrs:
            return _read_sparse(obj, cls)
        if cls == "struct" or cls is None:
            return _read_struct(f, obj)
        raise Unsupported(cls)
    if "MATLAB_object_decode" in obj.attrs:
        raise Unsupported(cls or "object")
    if _attr(obj, "MATLAB_empty") is not None:
        dims = tuple(int(d) for d in obj[()].reshape(-1))
        if cls == "char":
            return ""
        return np.zeros(dims if len(dims) == 2 else (0, 0))
    if cls == "cell":
        return _read_cell(f, obj)
    if cls == "char":
        return _read_char(obj)
    if cls == "function_handle":
        raise Unsupported(cls)
    if obj.dtype.kind == "O" and h5py.check_dtype(ref=obj.dtype):
        # a struct array's field: one reference per element
        return _read_cell(f, obj)
    return _read_numeric(obj, cls)


def _read_numeric(ds, cls):
    raw = ds[()]
    if raw.dtype.names and {"real", "imag"} <= set(raw.dtype.names):
        raw = raw["real"] + 1j * raw["imag"]
    arr = np.asarray(raw).T if raw.ndim else np.asarray(raw)
    if cls == "logical":
        return _normalise(arr.astype(bool))
    if arr.dtype.kind in "iu":
        arr = arr.astype(float)
    return _normalise(np.ascontiguousarray(arr))


def _read_char(ds):
    codes = np.asarray(ds[()]).T
    if codes.ndim == 1:
        codes = codes.reshape(1, -1)
    rows = ["".join(chr(int(c)) for c in row) for row in codes]
    return rows[0] if len(rows) == 1 else (Cell(rows, rows=len(rows))
                                           if rows else "")


def _read_cell(f, ds):
    refs = np.asarray(ds[()]).T
    if refs.ndim == 1:
        refs = refs.reshape(1, -1)
    rows = refs.shape[0]
    items = [_read(f, f[ref]) for ref in refs.reshape(-1, order="F")]
    return Cell(items, rows=rows) if items else Cell()


def _read_struct(f, group):
    names = _field_names(group)
    columns = {n: group[n] for n in names}
    arrays = [n for n, d in columns.items()
              if not hasattr(d, "keys") and d.dtype.kind == "O"
              and _attr(d, "MATLAB_class") is None]
    if not arrays:
        return Struct((n, _read(f, d)) for n, d in columns.items())
    shape = np.asarray(columns[arrays[0]][()]).T.shape
    if len(shape) == 1:
        shape = (1, shape[0])
    count = shape[0] * shape[1]
    elements = [Struct() for _ in range(count)]
    for n, d in columns.items():
        if n in arrays:
            refs = np.asarray(d[()]).T.reshape(-1, order="F")
            for k, ref in enumerate(refs):
                elements[k][n] = _read(f, f[ref])
        else:
            for k in range(count):
                elements[k][n] = _read(f, d)
    return StructArray(elements, rows=shape[0])


def _field_names(group) -> list[str]:
    stored = group.attrs.get("MATLAB_fields")
    if stored is not None:
        names = []
        for entry in np.asarray(stored).reshape(-1):
            raw = np.asarray(entry)
            if raw.dtype.kind == "S":
                names.append(raw.tobytes().decode("ascii", "replace"))
            else:
                names.append("".join(chr(int(c)) for c in raw.reshape(-1)))
        names = [n for n in names if n in group]
        if names:
            return names
    return [n for n in group if not n.startswith("#")]


def _read_sparse(group, cls):
    import scipy.sparse as sp

    from .lib_sparse import Sparse
    rows = int(group.attrs["MATLAB_sparse"])
    data = np.asarray(group["data"][()])
    ir = np.asarray(group["ir"][()]).astype(np.int64)
    jc = np.asarray(group["jc"][()]).astype(np.int64)
    if cls == "logical":
        data = data.astype(bool)
    if data.dtype.names and {"real", "imag"} <= set(data.dtype.names):
        data = data["real"] + 1j * data["imag"]
    return Sparse(sp.csc_matrix((data, ir, jc), shape=(rows, len(jc) - 1)))


# ── writing ───────────────────────────────────────────────────────

def save(path: str, variables: dict[str, Any]) -> None:
    """Write ``variables`` as a version 7.3 MAT-file."""
    h5py = _h5py()
    try:
        with h5py.File(path, "w", userblock_size=_USERBLOCK) as f:
            writer = _Writer(f)
            for name, value in variables.items():
                writer.put(f, name, value)
    except OSError as exc:
        raise MatlabError(f"Unable to write '{path}' ({exc}).") from None
    stamp = time.strftime("%a %b %d %H:%M:%S %Y")
    text = (f"MATLAB 7.3 MAT-file, Platform: Evans, Created on: {stamp} "
            f"HDF5 schema 1.00 .").encode("ascii")
    header = text.ljust(124, b" ")[:124] + b"\x00\x02IM"
    with open(path, "r+b") as fh:
        fh.write(header)


class _Writer:
    def __init__(self, f) -> None:
        self.f = f
        self.refs = f.require_group("#refs#")
        self.count = 0

    def _name(self) -> str:
        self.count += 1
        return f"e{self.count}"

    @staticmethod
    def _tag(obj, cls: str, **more) -> None:
        obj.attrs.create("MATLAB_class", np.bytes_(cls))
        for key, value in more.items():
            obj.attrs.create(key, value)

    def put(self, parent, name: str, value):
        """Write ``value`` as ``parent[name]``; returns the HDF5 object."""
        from .lib_sparse import Sparse
        if isinstance(value, Sparse):
            return self._sparse(parent, name, value)
        if isinstance(value, Struct):
            return self._struct(parent, name, value)
        if isinstance(value, StructArray):
            return self._struct_array(parent, name, value)
        if isinstance(value, Cell):
            return self._cell(parent, name, value)
        if isinstance(value, str):
            return self._char(parent, name, value)
        if value is None:
            return self._empty(parent, name, (0, 0), "double")
        if isinstance(value, (bool, int, float, complex, np.generic,
                              np.ndarray)):
            return self._numeric(parent, name, np.asarray(value))
        raise MatlabError(f"Cannot save '{name}': a "
                          f"{type(value).__name__} has no MAT-file form.")

    def _empty(self, parent, name, dims, cls):
        ds = parent.create_dataset(name, data=np.array(dims, dtype="u8"))
        self._tag(ds, cls, MATLAB_empty=np.uint8(1))
        return ds

    def _numeric(self, parent, name, a: np.ndarray):
        if a.ndim == 0:
            a = a.reshape(1, 1)
        elif a.ndim == 1:
            a = a.reshape(1, -1)
        cls = {"b": "logical", "f": "double", "c": "double", "i": "int64",
               "u": "uint64"}[a.dtype.kind]
        if a.dtype.kind in "fiu":
            cls = {np.dtype("float32"): "single"}.get(a.dtype, cls)
            if a.dtype.kind in "iu":
                cls = str(a.dtype)
        if a.size == 0:
            return self._empty(parent, name, a.shape, cls)
        stored = np.ascontiguousarray(a.T)
        if a.dtype.kind == "b":
            stored = stored.astype("u1")
        elif a.dtype.kind == "c":
            compound = np.dtype([("real", "<f8"), ("imag", "<f8")])
            packed = np.empty(stored.shape, compound)
            packed["real"], packed["imag"] = stored.real, stored.imag
            stored = packed
        ds = parent.create_dataset(name, data=stored)
        self._tag(ds, cls)
        return ds

    def _char(self, parent, name, text: str):
        if not text:
            return self._empty(parent, name, (0, 0), "char")
        codes = np.array([ord(c) for c in text], dtype="<u2").reshape(-1, 1)
        ds = parent.create_dataset(name, data=codes)
        self._tag(ds, "char", MATLAB_int_decode=np.int32(2))
        return ds

    def _sparse(self, parent, name, x):
        m = x.m.tocsc()
        m.sort_indices()
        g = parent.create_group(name)
        cls = "logical" if m.dtype == bool else "double"
        self._tag(g, cls, MATLAB_sparse=np.uint64(m.shape[0]))
        data = m.data.astype("u1") if m.dtype == bool else m.data
        if np.iscomplexobj(data):
            packed = np.empty(data.shape, np.dtype([("real", "<f8"),
                                                    ("imag", "<f8")]))
            packed["real"], packed["imag"] = data.real, data.imag
            data = packed
        g.create_dataset("data", data=data)
        g.create_dataset("ir", data=m.indices.astype("u8"))
        g.create_dataset("jc", data=m.indptr.astype("u8"))
        return g

    def _ref_array(self, items, rows, cols):
        """An HDF5 reference array for column-major ``items``."""
        h5py = _h5py()
        refs = np.empty((cols, rows), dtype=object)
        for k, item in enumerate(items):
            target = self.put(self.refs, self._name(), item)
            refs[k // rows, k % rows] = target.ref
        return refs, h5py.ref_dtype

    def _cell(self, parent, name, cell: Cell):
        if not len(cell):
            return self._empty(parent, name, (0, 0), "cell")
        rows, cols = cell.dims
        refs, dt = self._ref_array(cell, rows, cols)
        ds = parent.create_dataset(name, data=refs, dtype=dt)
        self._tag(ds, "cell")
        return ds

    def _fields_attr(self, group, names) -> None:
        h5py = _h5py()
        dt = h5py.vlen_dtype(np.dtype("S1"))
        arr = np.empty(len(names), dtype=dt)
        for k, n in enumerate(names):
            arr[k] = np.frombuffer(n.encode("ascii", "replace"), dtype="S1")
        group.attrs.create("MATLAB_fields", arr, dtype=dt)

    def _struct(self, parent, name, s: Struct):
        g = parent.create_group(name)
        self._tag(g, "struct")
        self._fields_attr(g, list(s))
        for key, value in s.items():
            self.put(g, key, value)
        return g

    def _struct_array(self, parent, name, arr: StructArray):
        if not len(arr):
            return self._empty(parent, name, (0, 0), "struct")
        rows, cols = arr.dims
        names = list(arr[0])
        g = parent.create_group(name)
        self._tag(g, "struct")
        self._fields_attr(g, names)
        h5py = _h5py()
        for key in names:
            refs, _ = self._ref_array([e.get(key) for e in arr], rows, cols)
            g.create_dataset(key, data=refs, dtype=h5py.ref_dtype)
        return g
