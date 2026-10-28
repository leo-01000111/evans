"""
Cells and structs.
==================
Mapping over arrays and cells, and converting between cells, structs and matrices.

A mixin of :class:`.matlab_runtime._Library`: each ``f_<name>`` method is
the MATLAB function ``<name>``. It is imported by :mod:`.matlab_runtime`
just before ``_Library`` is defined, so the helpers above that line can be
imported from it by name; anything defined further down is reached through
the module (``_mr._sprintf``) at call time. Import :mod:`.matlab_runtime` first, never this module on
its own: the two import each other.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping

import numpy as np

from . import matlab_runtime as _mr  # noqa: F401
from .matlab_runtime import (
    Cell,
    MatlabError,
    Struct,
    StructArray,
    _as2d,
    _as_array,
    _is_function,
    _is_lti,
    _is_number,
    _is_sym,
    _nargout,
    _normalise,
    _numel,
    _scalar,
    _shape,
)

# cellfun's old string forms, named by MATLAB for speed: cellfun('isempty', c).
_LEGACY = ("isempty", "islogical", "isreal", "length", "ndims", "prodofsize",
           "size", "isclass")


def _is_cellstr(x) -> bool:
    return isinstance(x, Cell) and all(isinstance(v, str) for v in x)


def _names(x, fn: str) -> list[str]:
    """A field name, or a cell of them, as a list."""
    if isinstance(x, str):
        return [x]
    if _is_cellstr(x):
        return list(x)
    raise MatlabError(f"{fn}: field names must be a character vector or a "
                      f"cell array of character vectors.")


def _elements(x) -> list:
    """``x``'s elements in MATLAB's linear (column-major) order."""
    if isinstance(x, Cell):
        return list(x)
    if isinstance(x, StructArray):
        return list(x)
    if isinstance(x, Struct):
        return [x]
    if isinstance(x, str):
        return list(x)
    a = _as2d(_as_array(x))
    flat = a.reshape(-1, order="F")
    if a.dtype == bool:
        return [bool(v) for v in flat]
    return [_scalar(v) for v in flat]


def _shaped_numbers(values: list, shape: tuple[int, int], dtype):
    a = np.array(values, dtype=dtype).reshape(shape, order="F") \
        if values else np.zeros(shape, dtype=dtype)
    out = _normalise(a)
    return _scalar(out) if not isinstance(out, np.ndarray) else out


def _struct_array(items: list, shape: tuple[int, int]):
    """Structs in the shape of the input: one, or an array of them."""
    if len(items) == 1:
        return items[0]
    return StructArray(items, rows=shape[0])


def _classify(v):
    """(class, value) of a scalar a uniform output may hold, else None."""
    if isinstance(v, (bool, np.bool_)):
        return "logical", bool(v)
    if _is_number(v):
        return "double", _scalar(v)
    if isinstance(v, str):
        return ("char", v) if len(v) == 1 else None
    if isinstance(v, Struct):
        return "struct", v
    if isinstance(v, StructArray):
        return ("struct", v[0]) if len(v) == 1 else None
    if isinstance(v, np.ndarray) and v.size == 1 and v.dtype != object:
        item = v.reshape(-1)[0]
        if v.dtype == bool:
            return "logical", bool(item)
        if v.dtype.kind in "U":
            return "char", str(item)
        if v.dtype.kind in "biufc":
            return "double", _scalar(item)
    return None


def _equal(a, b, nan_equal: bool) -> bool:
    """MATLAB's isequal of two values."""
    if isinstance(a, StructArray) and len(a) == 1:
        a = a[0]
    if isinstance(b, StructArray) and len(b) == 1:
        b = b[0]
    if isinstance(a, Cell) or isinstance(b, Cell):
        return (isinstance(a, Cell) and isinstance(b, Cell)
                and a.dims == b.dims
                and all(_equal(x, y, nan_equal) for x, y in zip(a, b)))
    if isinstance(a, StructArray) or isinstance(b, StructArray):
        return (isinstance(a, StructArray) and isinstance(b, StructArray)
                and _shape(a) == _shape(b)
                and all(_equal(x, y, nan_equal) for x, y in zip(a, b)))
    if isinstance(a, Mapping) or isinstance(b, Mapping):
        # Field order does not matter, only the names and the values.
        return (isinstance(a, Mapping) and isinstance(b, Mapping)
                and set(a) == set(b)
                and all(_equal(a[k], b[k], nan_equal) for k in a))
    if _is_function(a) or _is_function(b):
        return a is b
    if _is_lti(a) or _is_lti(b):
        raise MatlabError("isequal does not compare systems in Evans; "
                          "compare their tfdata or ssdata instead.")
    if _is_sym(a) or _is_sym(b):
        if _shape(a) != _shape(b):
            return False
        try:
            return bool(np.all(np.asarray(a == b)))
        except TypeError:
            return False
    if a is None or b is None:
        return _numel(a) == 0 and _numel(b) == 0 and _shape(a) == _shape(b)
    x, y = _codes(a), _codes(b)
    if x is None or y is None:
        raise MatlabError(f"isequal cannot compare a "
                          f"{type(a if x is None else b).__name__} in Evans.")
    if _shape(a) != _shape(b):
        return False
    return bool(np.array_equal(x, y, equal_nan=nan_equal))


def _codes(x):
    """A numeric, logical or char value as a 2-D numeric array, else None."""
    if isinstance(x, str):
        return np.array([[ord(ch) for ch in x]], dtype=float) if x \
            else np.zeros((0, 0))
    if not (_is_number(x) or isinstance(x, (np.ndarray, list))):
        return None
    a = _as2d(_as_array(x))
    if a.dtype == object:
        return None
    if a.dtype.kind in "U":
        a = np.vectorize(ord)(a) if a.size else np.zeros(a.shape)
    return a.astype(complex) if np.iscomplexobj(a) else a.astype(float)


class CellLibrary:
    """cellfun, cell2mat, rmfield and the rest."""

    # ── cellfun and arrayfun ────────────────────────────────────

    @_nargout
    def f_cellfun(self, func, *args, nargout=1):
        inputs, uniform = self._map_options("cellfun", args)
        if isinstance(func, str) and func in _LEGACY:
            return self._cellfun_legacy(func, inputs)
        for k, c in enumerate(inputs, 1):
            if not isinstance(c, Cell):
                raise MatlabError(f"cellfun: input #{k + 1} must be a cell "
                                  f"array; use arrayfun for other arrays.")
        return self._map("cellfun", func, inputs, uniform, nargout)

    @_nargout
    def f_arrayfun(self, func, *args, nargout=1):
        inputs, uniform = self._map_options("arrayfun", args)
        for x in inputs:
            if _is_lti(x) or _is_sym(x):
                raise MatlabError("arrayfun over a system or a symbolic "
                                  "array is not supported in Evans.")
        # Each element of a cell reaches the function as a 1×1 cell.
        return self._map("arrayfun", func, inputs, uniform, nargout,
                         wrap_cells=True)

    @staticmethod
    def _map_options(fn: str, args: tuple) -> tuple[list, bool]:
        """Split cellfun's inputs from its trailing 'Name', value options."""
        inputs, uniform = list(args), True
        for k, a in enumerate(args):
            if isinstance(a, str) and a.lower() in ("uniformoutput",
                                                    "errorhandler"):
                inputs, options = list(args[:k]), args[k:]
                break
        else:
            options = ()
        if len(options) % 2:
            raise MatlabError(f"{fn}: every option name needs a value.")
        for name, value in zip(options[0::2], options[1::2]):
            key = str(name).lower()
            if key == "uniformoutput":
                uniform = bool(np.all(_as_array(value)))
            elif key == "errorhandler":
                raise MatlabError(f"{fn}'s 'ErrorHandler' option is not "
                                  f"supported in Evans; use try/catch in "
                                  f"the function instead.")
            else:
                raise MatlabError(f"{fn}: unknown option '{name}'.")
        if not inputs:
            raise MatlabError("Not enough input arguments.")
        return inputs, uniform

    def _map(self, fn: str, func, inputs: list, uniform: bool,
             nargout: int, wrap_cells: bool = False):
        if isinstance(func, str):
            func = self.rt.lookup(func, {}, {})
        if not callable(func):
            raise MatlabError(f"{fn}: the first input must be a function "
                              f"handle.")
        shape = _shape(inputs[0])
        for k, x in enumerate(inputs[1:], 3):
            if _shape(x) != shape:
                raise MatlabError(
                    f"All of the input arguments must be of the same size "
                    f"and shape.\nPrevious inputs had size "
                    f"{shape[0]}×{shape[1]}; input #{k} has size "
                    f"{_shape(x)[0]}×{_shape(x)[1]}.",
                    f"MATLAB:{fn}:ArgumentDimensionMismatch")
        columns = []
        for x in inputs:
            items = _elements(x)
            if wrap_cells and isinstance(x, Cell):
                items = [Cell([v]) for v in items]
            columns.append(items)
        count = max(nargout, 1)
        results = []                      # one tuple of outputs per element
        for i in range(shape[0] * shape[1]):
            out = self.rt.call(func, tuple(col[i] for col in columns),
                               nargout=nargout)
            results.append(self.rt.unpack(out, count) if count > 1
                           else (out,))
        if nargout == 0 and all(r[0] is None for r in results):
            return None
        outputs = [self._collect(fn, [r[j] for r in results], shape, j,
                                 uniform) for j in range(count)]
        return tuple(outputs) if count > 1 else outputs[0]

    @staticmethod
    def _collect(fn: str, values: list, shape: tuple[int, int], j: int,
                 uniform: bool):
        """Output ``j`` of every call, shaped as the input."""
        if not uniform:
            return Cell(values, rows=shape[0])
        if not values:
            return np.zeros(shape)
        kind = None
        picked = []
        for i, v in enumerate(values, 1):
            got = _classify(v)
            if got is None:
                raise MatlabError(
                    f"Non-scalar in Uniform output, at index {i}, output "
                    f"{j + 1}.\nSet 'UniformOutput' to false.",
                    f"MATLAB:{fn}:NotAScalarOutput")
            if kind is not None and got[0] != kind:
                raise MatlabError(
                    f"Mismatch in type of outputs, at index {i}, output "
                    f"{j + 1} ({got[0]} versus {kind}).\nSet "
                    f"'UniformOutput' to false.",
                    f"MATLAB:{fn}:MismatchInOutputTypes")
            kind = got[0]
            picked.append(got[1])
        if kind == "logical":
            return _shaped_numbers(picked, shape, bool)
        if kind == "double":
            dtype = complex if any(isinstance(v, complex) for v in picked) \
                else float
            return _shaped_numbers(picked, shape, dtype)
        if kind == "char":
            if shape[0] > 1:
                raise MatlabError("Evans has no multi-row char arrays; set "
                                  "'UniformOutput' to false for a cell.")
            return "".join(picked)
        fields = set(picked[0])
        if any(set(s) != fields for s in picked):
            raise MatlabError("Concatenation of structures requires the same "
                              "field names.")
        return _struct_array(picked, shape)

    def _cellfun_legacy(self, name: str, inputs: list):
        c, extra = inputs[0], inputs[1:]
        if not isinstance(c, Cell):
            raise MatlabError("cellfun: the second input must be a cell "
                              "array.")
        shape = c.dims
        if name in ("size", "isclass"):
            if len(extra) != 1:
                raise MatlabError(f"cellfun('{name}', c, ...) needs one more "
                                  f"input.")
            arg = extra[0]
        elif extra:
            raise MatlabError("Too many input arguments.")
        if name == "isempty":
            out = [_numel(v) == 0 for v in c]
        elif name == "islogical":
            out = [self.f_class(v) == "logical" for v in c]
        elif name == "isreal":
            out = [not isinstance(v, (Cell, Mapping, StructArray))
                   and bool(self.f_isreal(v)) for v in c]
        elif name == "isclass":
            out = [self.f_class(v) == arg for v in c]
        elif name == "length":
            out = [float(self.f_length(v)) for v in c]
        elif name == "ndims":
            out = [2.0] * len(c)
        elif name == "prodofsize":
            out = [float(_numel(v)) for v in c]
        else:                                                # size
            k = int(arg)
            out = [float(_shape(v)[k - 1]) if k <= 2 else 1.0 for v in c]
        dtype = bool if name.startswith("is") else float
        return _shaped_numbers(out, shape, dtype)

    # ── cells ↔ matrices and structs ────────────────────────────

    def f_cell2mat(self, c):
        if not isinstance(c, Cell):
            raise MatlabError("cell2mat: the input must be a cell array.",
                              "MATLAB:cell2mat:InvalidInput")
        if not len(c):
            return np.zeros((0, 0))
        first = c[0]
        if isinstance(first, Cell) or not (
                isinstance(first, (str, np.ndarray, Mapping, StructArray))
                or _is_number(first)):
            raise MatlabError("CELL2MAT does not support cell arrays "
                              "containing cell arrays or objects.",
                              "MATLAB:cell2mat:UnsupportedCellContent")
        kind = self.f_class(first)
        if any(self.f_class(v) != kind for v in c):
            raise MatlabError("All contents of the input cell array must be "
                              "of the same data type.",
                              "MATLAB:cell2mat:MixedDataTypes")
        if kind == "struct":
            raise MatlabError("cell2mat of a cell of structs is not "
                              "supported in Evans; index the cell instead.")
        rows = []
        for row in c.grid():
            blocks = [self._block(v) for v in row]
            blocks = [b for b in blocks if b.size or b.shape != (0, 0)]
            if blocks:
                if len({b.shape[0] for b in blocks}) > 1:
                    raise MatlabError("Dimensions of arrays being "
                                      "concatenated are not consistent.")
                rows.append(np.hstack(blocks))
        rows = [r for r in rows if r.size or r.shape != (0, 0)]
        if not rows:
            return "" if kind == "char" else np.zeros((0, 0))
        if len({r.shape[1] for r in rows}) > 1:
            raise MatlabError("Dimensions of arrays being concatenated are "
                              "not consistent.")
        out = np.vstack(rows)
        if kind == "char":
            if out.shape[0] > 1:
                raise MatlabError("Evans has no multi-row char arrays; this "
                                  "cell2mat would make one.")
            return "".join(chr(int(v)) for v in out.reshape(-1))
        result = _normalise(out)
        return _scalar(result) if not isinstance(result, np.ndarray) \
            else result

    @staticmethod
    def _block(v) -> np.ndarray:
        if isinstance(v, str):
            return np.array([[ord(ch) for ch in v]], dtype=float) if v \
                else np.zeros((0, 0))
        a = _as_array(v)
        if a.ndim == 1 and a.size == 0:
            return np.zeros((0, 0), dtype=a.dtype)
        return _as2d(a)

    def f_struct2cell(self, s):
        if isinstance(s, Struct):
            return Cell(s.values(), rows=len(s))
        if not isinstance(s, StructArray):
            raise MatlabError("struct2cell: the input must be a struct.")
        r, n = _shape(s)
        fields = list(s[0]) if len(s) else []
        if r * n == 1:
            return Cell(s[0].values(), rows=len(fields))
        if n > 1:
            raise MatlabError(
                f"struct2cell of a 1×{n} struct array is {len(fields)}×1×{n} "
                f"in MATLAB, and Evans supports 2-D arrays only; convert one "
                f"element at a time, struct2cell(s(k)).")
        # An m×1 struct array: one column of values per element.
        return Cell((e[f] for e in s for f in fields), rows=len(fields))

    def f_cell2struct(self, c, fields, dim=1):
        if not isinstance(c, Cell):
            raise MatlabError("cell2struct: the first input must be a cell "
                              "array.")
        names = _names(fields, "cell2struct")
        dim = int(dim)
        if dim not in (1, 2):
            raise MatlabError("Evans supports matrices (2-D) only; dim must "
                              "be 1 or 2.")
        grid = c.grid() if len(c) else []
        r, n = c.dims
        if dim == 2:                       # fields along the rows instead
            grid = [list(col) for col in zip(*grid)] if grid else []
            r, n = n, r
        if len(names) != r:
            raise MatlabError("Number of field names must match number of "
                              "fields in new structure.",
                              "MATLAB:cell2struct:ArgDimensionMismatch")
        if len(set(names)) != len(names):
            raise MatlabError("Duplicate field names are not allowed.")
        items = [Struct({f: grid[i][j] for i, f in enumerate(names)})
                 for j in range(n)]
        # MATLAB's result is an n×1 column of structs.
        return items[0] if n == 1 else StructArray(items, rows=n)

    # ── struct fields ───────────────────────────────────────────

    def f_rmfield(self, s, fields):
        names = _names(fields, "rmfield")
        elems = [s] if isinstance(s, Struct) else (
            list(s) if isinstance(s, StructArray) else None)
        if elems is None:
            raise MatlabError("rmfield: the first input must be a struct.")
        present = list(elems[0]) if elems else []
        for f in names:
            if f not in present:
                raise MatlabError(f"A field named '{f}' doesn't exist.",
                                  "MATLAB:rmfield:InvalidFieldname")
        out = [Struct({k: v for k, v in e.items() if k not in names})
               for e in elems]
        return out[0] if isinstance(s, Struct) else StructArray(
            out, rows=_shape(s)[0])

    @_nargout
    def f_orderfields(self, s, order=None, nargout=1):
        elems = [s] if isinstance(s, Struct) else (
            list(s) if isinstance(s, StructArray) else None)
        if elems is None:
            raise MatlabError("orderfields: the first input must be a "
                              "struct.")
        fields = list(elems[0]) if elems else []
        if order is None:
            new = sorted(fields)              # code order: 'B' before 'a'
        elif isinstance(order, (Struct, StructArray)):
            new = list(order if isinstance(order, Struct) else
                       (order[0] if len(order) else {}))
        elif isinstance(order, Cell):
            new = _names(order, "orderfields")
        else:
            perm = [int(v) for v in np.asarray(order, dtype=float).ravel()]
            if sorted(perm) != list(range(1, len(fields) + 1)):
                raise MatlabError("orderfields: the permutation must contain "
                                  "each field's position exactly once.",
                                  "MATLAB:orderfields:InvalidPermutation")
            new = [fields[k - 1] for k in perm]
        if sorted(new) != sorted(fields):
            raise MatlabError("orderfields: the new order must name exactly "
                              "the fields of the struct, each once.",
                              "MATLAB:orderfields:InvalidFieldNames")
        out = [Struct({f: e[f] for f in new}) for e in elems]
        result = out[0] if isinstance(s, Struct) else StructArray(
            out, rows=_shape(s)[0])
        if nargout < 2:
            return result
        perm = np.array([[fields.index(f) + 1.0] for f in new]) \
            if new else np.zeros((0, 1))
        perm = _normalise(perm)
        return result, _scalar(perm) if not isinstance(perm, np.ndarray) \
            else perm

    def f_isfield(self, s, name):
        fields = (list(s) if isinstance(s, Mapping) else
                  list(s[0]) if isinstance(s, StructArray) and len(s)
                  else None)
        if isinstance(name, Cell):
            hits = [fields is not None and isinstance(n, str) and n in fields
                    for n in name]
            return _shaped_numbers(hits, name.dims, bool)
        return fields is not None and isinstance(name, str) and name in fields

    def f_getfield(self, s, *path):
        if not path:
            raise MatlabError("Not enough input arguments.")
        value = s
        for name in path:
            if not isinstance(name, str):
                raise MatlabError("getfield with index arguments {i} is not "
                                  "supported in Evans; index the struct "
                                  "directly, s(i).name.")
            if isinstance(value, StructArray) and len(value) != 1:
                raise MatlabError("getfield of a struct array is not "
                                  "supported in Evans; use s(k).name.")
            value = self.rt.field(value, name)
        return value

    def f_setfield(self, s, *args):
        if len(args) < 2:
            raise MatlabError("Not enough input arguments.")
        *path, value = args
        if not all(isinstance(p, str) for p in path):
            raise MatlabError("setfield with index arguments {i} is not "
                              "supported in Evans; assign s(i).name = v.")
        if isinstance(s, StructArray) and len(s) != 1:
            raise MatlabError("setfield of a struct array is not supported "
                              "in Evans; use s(k).name = v.")
        return self.rt.assign(s, [(".", p) for p in path], value)

    def f_iscellstr(self, x):
        return _is_cellstr(x)

    @_nargout
    def f_deal(self, *args, nargout=1):
        count = max(nargout, 1)
        if len(args) == 1:
            values = (args[0],) * count
        elif len(args) == count:
            values = args
        else:
            raise MatlabError("The number of outputs should match the number "
                              "of inputs.", "MATLAB:deal:narginchk")
        values = tuple(copy.copy(v) for v in values)
        return values if count > 1 else values[0]

    # ── comparisons ─────────────────────────────────────────────

    def f_isequal(self, a, b, *more):
        others = (b,) + more
        return all(_equal(a, x, False) for x in others)

    def f_isequaln(self, a, b, *more):
        others = (b,) + more
        return all(_equal(a, x, True) for x in others)

    @_nargout
    def f_ismember(self, a, s, *options, nargout=1):
        rows = False
        for opt in options:
            if isinstance(opt, str) and opt.lower() == "rows":
                rows = True
            else:
                raise MatlabError(f"ismember: option '{opt}' is not "
                                  f"supported in Evans.")
        if isinstance(a, Cell) or isinstance(s, Cell):
            if rows:
                raise MatlabError("ismember: 'rows' does not apply to cell "
                                  "arrays.")
            tf, loc = self._ismember_text(a, s)
        elif rows:
            tf, loc = self._ismember_rows(a, s)
        else:
            x, y = _codes(a), _codes(s)
            if x is None or y is None:
                raise MatlabError("ismember: inputs must be numeric, logical, "
                                  "char or cell arrays of character "
                                  "vectors.")
            flat = y.reshape(-1, order="F")
            hits = []
            for v in x.reshape(-1, order="F"):
                where = np.nonzero(flat == v)[0]      # NaN matches nothing
                hits.append(int(where[0]) + 1 if where.size else 0)
            shape = _shape(a)
            tf = _shaped_numbers([h > 0 for h in hits], shape, bool)
            loc = _shaped_numbers([float(h) for h in hits], shape, float)
        return (tf, loc) if nargout >= 2 else tf

    @staticmethod
    def _ismember_text(a, s):
        def bad():
            return MatlabError(
                f"Input A of class {'cell' if isinstance(a, Cell) else 'char'}"
                f" and input B of class "
                f"{'cell' if isinstance(s, Cell) else 'char'} must be cell "
                f"arrays of character vectors, unless one is a character "
                f"vector.", "MATLAB:ISMEMBER:InputClass")
        if isinstance(s, str):
            s = Cell([s])
        if not _is_cellstr(s):
            raise bad()
        lookup = list(s)
        if isinstance(a, str):
            k = lookup.index(a) + 1 if a in lookup else 0
            return k > 0, k
        if not _is_cellstr(a):
            raise bad()
        hits = [lookup.index(v) + 1 if v in lookup else 0 for v in a]
        shape = a.dims
        return (_shaped_numbers([h > 0 for h in hits], shape, bool),
                _shaped_numbers([float(h) for h in hits], shape, float))

    @staticmethod
    def _ismember_rows(a, s):
        x, y = _codes(a), _codes(s)
        if x is None or y is None:
            raise MatlabError("ismember: 'rows' needs numeric, logical or "
                              "char matrices.")
        if x.shape[1] != y.shape[1] and x.size and y.size:
            raise MatlabError("A and S must have the same number of columns.",
                              "MATLAB:ISMEMBER:AandBColnumAgree")
        hits = []
        for row in x:
            where = [k for k, other in enumerate(y) if np.array_equal(row,
                                                                     other)]
            hits.append(where[0] + 1 if where else 0)
        shape = (len(hits), 1)
        return (_shaped_numbers([h > 0 for h in hits], shape, bool),
                _shaped_numbers([float(h) for h in hits], shape, float))
