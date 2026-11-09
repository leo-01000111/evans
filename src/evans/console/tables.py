"""
The table.
==========
:class:`ColumnTable` is what ``table``, ``readtable``, ``array2table`` and
the table functions return and take: named variables of equal height, one
column each. A column is one of

* a 1-D numpy array (double, logical or complex),
* a list of ``str`` (a cell array of char vectors),
* a :class:`.lib_dates.Datetime` or :class:`.lib_dates.Duration` column.

``T(rows, vars)`` reaches the table through ``Runtime.call`` (a table is
callable), ``T{rows, cols}`` through ``Runtime.cell_index``, ``T.Name``
through ``Runtime.field`` and every assignment through
``Runtime.assign``, which hands it to :meth:`ColumnTable._ml_assign`; a
table is a value, so each assignment works on a copy.

A :class:`Timetable` is a table whose rows are labelled by a datetime or
duration vector (``time``); ``columns`` holds the data variables only, so
``size``, ``width`` and ``T(rows, vars)`` count them the way MATLAB does.
"""

from __future__ import annotations

import math

import numpy as np

from . import matlab_runtime as _mr  # noqa: F401
from .lib_dates import Datetime, Duration, _Vec, parse_one
from .matlab_runtime import (
    COLON,
    TABLE_WIDTH,
    Cell,
    MatlabError,
    Struct,
    StructArray,
    Table,
    _as_array,
    _normalise,
)

# ──────────────────────────────────────────────────────────────
#  Columns
# ──────────────────────────────────────────────────────────────


def col_take(col, idx):
    idx = np.asarray(idx, dtype=int).reshape(-1)
    if isinstance(col, np.ndarray):
        return col[idx]
    if isinstance(col, _Vec):
        return col.take(idx)
    return [col[i] for i in idx]


def col_blank(col, n: int):
    """``n`` missing values of the same kind as ``col``."""
    if isinstance(col, _Vec):
        return col.blank(n, col.fmt)
    if isinstance(col, np.ndarray):
        if col.dtype == bool:
            return np.zeros(n, dtype=bool)
        return np.full(n, np.nan, dtype=col.dtype)
    return [""] * n


def col_concat(a, b):
    if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
        if a.dtype == bool and b.dtype == bool:
            return np.concatenate([a, b])
        return np.concatenate([a.astype(complex if np.iscomplexobj(a)
                                        or np.iscomplexobj(b) else float),
                               b.astype(complex if np.iscomplexobj(a)
                                        or np.iscomplexobj(b) else float)])
    if isinstance(a, list) and isinstance(b, list):
        return a + b
    if type(a) is type(b) and isinstance(a, _Vec):
        return a._new(np.concatenate([a.flat(), b.flat()]).reshape(-1, 1))
    raise MatlabError("Unable to concatenate table variables of different "
                      "types.")


def col_set(col, rows, vals):
    """A copy of ``col`` with ``rows`` set from ``vals`` (a column)."""
    rows = np.asarray(rows, dtype=int)
    if isinstance(col, np.ndarray):
        if not isinstance(vals, np.ndarray):
            raise MatlabError("Unable to assign text to a numeric table "
                              "variable.")
        out = col
        if (vals.dtype != bool and out.dtype == bool):
            out = out.astype(float)
        if np.iscomplexobj(vals) and not np.iscomplexobj(out):
            out = out.astype(complex)
        out = out.copy()
        out[rows] = vals if out.dtype != bool else vals.astype(bool)
        return out
    if isinstance(col, list):
        if not isinstance(vals, list):
            raise MatlabError("Unable to assign a number to a text table "
                              "variable; use {'text'}.")
        out = list(col)
        for r, v in zip(rows, vals):
            out[r] = v
        return out
    if type(col) is not type(vals):
        raise MatlabError(f"Unable to assign a {type(vals).__name__.lower()}"
                          f" to a {col.ml_class} table variable.")
    flat = col.flat().copy()
    flat[rows] = vals.flat()
    return col._new(flat.reshape(-1, 1))


def col_texts(col):
    """(text per row, right-aligned?) for display."""
    if isinstance(col, _Vec):
        return col.texts(), True
    if isinstance(col, list):
        return (["{" + _mr._brief(v) + "}" if isinstance(v, str) and v
                 else "{0×0 char}" if v == "" else _mr._brief(v)
                 for v in col], False)
    if col.dtype == bool:
        return (["true" if v else "false" for v in col], False)
    return [short_g(v) for v in col], True


def short_g(v) -> str:
    """How a table shows a number: ``format short g``."""
    if isinstance(v, (complex, np.complexfloating)):
        return _mr._number(complex(v))
    v = float(v)
    if math.isnan(v):
        return "NaN"
    if math.isinf(v):
        return "Inf" if v > 0 else "-Inf"
    if v.is_integer() and abs(v) < 1e10:
        return str(int(v))
    return f"{v:.5g}"


def col_value(col):
    """A column as the MATLAB value ``T.Name`` gives."""
    if isinstance(col, np.ndarray):
        return _normalise(col.reshape(-1, 1))
    if isinstance(col, _Vec):
        return col._new(col.flat().reshape(-1, 1))
    return Cell(col, rows=len(col))


def col_keys(col):
    """One hashable, orderable key per row (missing sorts last)."""
    if isinstance(col, _Vec):
        k = col.keys()
        miss = np.isnat(col.flat()) if isinstance(col, Datetime) \
            else np.isnan(col.flat())
        return [(1, 0) if m else (0, int(v) if isinstance(col, Datetime)
                                  else float(v))
                for v, m in zip(k, miss)]
    if isinstance(col, list):
        return [(0, v) if isinstance(v, str) else (0, "") for v in col]
    return [(1, 0.0) if (isinstance(v, (float, complex, np.floating))
                         and v != v) else (0, v.item()
                                           if hasattr(v, "item") else v)
            for v in col]


def to_col(value, k: int, n: int | None = None):
    """A MATLAB value → one table variable (a column)."""
    if isinstance(value, _Vec):
        if value.a.shape[0] != 1 and value.a.shape[1] != 1:
            raise MatlabError(f"Argument {k} is a matrix; a table variable "
                              f"must be a column.")
        flat = value.flat()
        if n is not None and flat.size == 1 and n != 1:
            flat = np.repeat(flat, n)
        return value._new(flat.reshape(-1, 1))
    if isinstance(value, Cell):
        r, c = value.dims
        if c != 1 and len(value) and r == 1 and c >= 1:
            raise MatlabError(
                f"Argument {k} is a 1×{c} cell; a table variable must "
                f"be a column, such as {{'a'; 'b'}}.")
        items = list(value)
        if n is not None and len(items) == 1 and n != 1:
            items = items * n
        return items
    if isinstance(value, str):
        if n is not None:
            return [value] * n
        raise MatlabError("A char vector as a table variable is not "
                          "supported in Evans; put the text in a cell, such "
                          "as {'abc'}.")
    if isinstance(value, (Struct, StructArray, Table)) or callable(value):
        raise MatlabError(f"Evans's tables hold numbers, logicals, text, "
                          f"datetimes and durations; argument {k} is none "
                          f"of these.")
    a = _as_array(value)
    if a.ndim == 0:
        a = a.reshape(1)
    if a.ndim == 1 and a.size > 1:
        raise MatlabError(
            f"Argument {k} is a row vector; a table variable must be a "
            f"column. Transpose it with ' first.")
    if a.ndim == 2:
        if a.shape[1] != 1 and a.size:
            raise MatlabError(
                f"Argument {k} is a {a.shape[0]}×{a.shape[1]} matrix; "
                f"Evans's tables hold one column per variable. Use "
                f"array2table to split a matrix into variables.")
        a = a.reshape(-1)
    if a.dtype == bool:
        out = a.copy()
    elif np.iscomplexobj(a):
        out = a.astype(complex)
    else:
        out = a.astype(float)
    if n is not None and out.size == 1 and n != 1:
        out = np.repeat(out, n)
    return out


def _positions(arg, n: int) -> list[int]:
    """A MATLAB subscript as 0-based positions; a call's ``:`` is None."""
    arg = COLON if arg is None else arg
    return np.atleast_1d(_mr.Runtime._indices(None, arg, n)).tolist()


def _is_colon(arg) -> bool:
    return arg is None or arg is COLON or (isinstance(arg, str)
                                           and arg == ":")


class TimeRange:
    """``timerange(t1, t2)``: a row subscript of a timetable."""

    ml_class = "timerange"

    def __init__(self, lo, hi, interval="openright") -> None:
        self.lo, self.hi, self.interval = lo, hi, interval

    def __repr__(self) -> str:
        return f"timerange({self.lo!r}, {self.hi!r}, '{self.interval}')"

    def mask(self, time: _Vec) -> np.ndarray:
        lo, hi = self.lo, self.hi
        if isinstance(time, Datetime):
            lo = _to_time(lo, time)
            hi = _to_time(hi, time)
        k = time.keys()
        kl, kh = lo.keys()[0], hi.keys()[0]
        left = k > kl if self.interval in ("open", "openleft") else k >= kl
        right = k < kh if self.interval in ("open", "openright") else k <= kh
        return left & right


def _to_time(x, like):
    if isinstance(x, str):
        v = parse_one(x, None)
        if v is None:
            raise MatlabError(f"Unable to read '{x}' as a datetime.")
        return Datetime(np.array([[v]]))
    return x


# ──────────────────────────────────────────────────────────────
#  The table
# ──────────────────────────────────────────────────────────────

class _Rows:
    """``Table.rows`` for a column table: rows as mappings, built lazily."""

    def __init__(self, table: ColumnTable) -> None:
        self.table = table

    def __len__(self) -> int:
        return self.table.height

    def __getitem__(self, i):
        if isinstance(i, slice):
            return [self[k] for k in range(*i.indices(len(self)))]
        return {n: (c[i].item() if isinstance(c, np.ndarray)
                    else c[i] if isinstance(c, list) else c.texts()[i])
                for n, c in zip(self.table.columns, self.table._data)}

    def __iter__(self):
        return (self[i] for i in range(len(self)))


class ColumnTable(Table):
    ml_class = "table"

    def __init__(self, names, data, descriptions=None, height=None,
                 row_names=None) -> None:
        names = [str(n) for n in names]
        if "Properties" in names:
            raise MatlabError("'Properties' is a reserved name and cannot be "
                              "used as a table variable name.")
        if len(set(names)) != len(names):
            dup = next(n for n in names if names.count(n) > 1)
            raise MatlabError(f"Duplicate table variable name: '{dup}'.")
        heights = {len(c) for c in data}
        if len(heights) > 1:
            raise MatlabError("All table variables must have the same number "
                              "of rows.")
        self.columns = names
        self._data = list(data)
        self._height = heights.pop() if heights else (height or 0)
        self._descriptions = list(descriptions) if descriptions else []
        self.row_names = list(row_names) if row_names else None
        if self.row_names is not None:
            if len(self.row_names) != self._height:
                raise MatlabError("The RowNames property must contain one "
                                  "name for each row in the table.")
            if len(set(self.row_names)) != len(self.row_names):
                dup = next(n for n in self.row_names
                           if self.row_names.count(n) > 1)
                raise MatlabError(f"Duplicate row name: '{dup}'.")
        self.description = ""

    # a copy to write into -------------------------------------------
    def copy(self):
        t = type(self).__new__(type(self))
        t.__dict__.update(self.__dict__)
        t.columns = list(self.columns)
        t._data = list(self._data)
        t._descriptions = list(self._descriptions)
        t.row_names = list(self.row_names) if self.row_names else None
        return t

    def _like(self, names, data, desc=None, height=None, row_names=None,
              time=None):
        """A table of this kind built from the pieces given."""
        t = ColumnTable(names, data, desc, height, row_names)
        t.description = self.description
        return t

    @property
    def rows(self):
        return _Rows(self)

    @property
    def height(self) -> int:
        return self._height

    # T.Name and T.Properties ----------------------------------------
    def properties(self) -> Struct:
        return Struct(
            Description=self.description,
            VariableNames=Cell(self.columns, rows=1),
            VariableDescriptions=Cell(self._descriptions, rows=1),
            RowNames=(Cell(self.row_names, rows=len(self.row_names))
                      if self.row_names else Cell()),
            DimensionNames=Cell(["Row", "Variables"], rows=1))

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        if name == "Properties":
            return self.properties()
        cols = self.__dict__.get("columns", [])
        if name in cols:
            return self.variable(cols.index(name))
        raise AttributeError(f"Unrecognized table variable name '{name}'.")

    def variable(self, k: int):
        return col_value(self._data[k])

    def is_text(self, k: int) -> bool:
        return isinstance(self._data[k], list)

    def _var_indices(self, arg) -> list[int]:
        if _is_colon(arg):
            return list(range(len(self.columns)))
        if isinstance(arg, str):
            arg = [arg]
        if isinstance(arg, (Cell, list)):
            out = []
            for name in arg:
                if name not in self.columns:
                    raise MatlabError(
                        f"Unrecognized table variable name '{name}'.")
                out.append(self.columns.index(name))
            return out
        return _positions(arg, len(self.columns))

    def _row_indices(self, arg) -> list[int]:
        if _is_colon(arg):
            return list(range(self.height))
        if isinstance(arg, str) or (isinstance(arg, Cell) and len(arg)
                                    and all(isinstance(v, str)
                                            for v in arg)):
            names = [arg] if isinstance(arg, str) else list(arg)
            if not self.row_names:
                raise MatlabError("This table has no row names; index its "
                                  "rows by number.")
            out = []
            for n in names:
                if n not in self.row_names:
                    raise MatlabError(f"Unrecognized row name '{n}'.")
                out.append(self.row_names.index(n))
            return out
        return _positions(arg, self.height)

    # T(rows, vars) --------------------------------------------------
    def __call__(self, *args, **_):
        if len(args) == 1:
            raise MatlabError("Subscripting into a table using one subscript "
                              "(as in t(i)) is not supported. Specify a row "
                              "subscript and a variable subscript, as in "
                              "t(rows,vars).")
        if len(args) != 2:
            raise MatlabError("Tables are two-dimensional: index as "
                              "t(rows, vars).")
        rows = self._row_indices(args[0])
        ks = self._var_indices(args[1])
        return self.select(rows, ks)

    def select(self, rows, ks):
        data = [col_take(self._data[k], rows) for k in ks]
        desc = ([self._descriptions[k] for k in ks]
                if self._descriptions else [])
        rn = [self.row_names[i] for i in rows] if self.row_names else None
        return self._like([self.columns[k] for k in ks], data, desc,
                          len(rows), rn)

    # T{rows, cols} --------------------------------------------------
    def brace(self, args):
        if len(args) != 2:
            raise MatlabError("Tables are two-dimensional: index as "
                              "T{rows, vars}.")
        rows = self._row_indices(args[0])
        ks = self._var_indices(args[1])
        return self._concat_vars(rows, ks)

    def _concat_vars(self, rows, ks):
        parts = [col_take(self._data[k], rows) for k in ks]
        if not parts:
            return np.zeros((len(rows), 0))
        texts = [isinstance(p, list) for p in parts]
        if all(texts):
            grid = [[p[i] for p in parts] for i in range(len(rows))]
            if len(grid) == 1 and len(grid[0]) == 1:
                return Cell(grid[0], rows=1)
            return Cell.from_grid(grid) if grid else Cell()
        if any(texts):
            a = texts.index(True)
            b = texts.index(False)
            j, k = sorted((a, b))
            ta = "cell" if texts[j] else "double"
            tb = "cell" if texts[k] else "double"
            raise MatlabError(
                f"Unable to concatenate the table variables "
                f"'{self.columns[ks[j]]}' and '{self.columns[ks[k]]}', "
                f"because their types are {ta} and {tb}.")
        if all(isinstance(p, _Vec) for p in parts):
            if len(parts) == 1:
                return parts[0]._new(parts[0].flat().reshape(-1, 1))
            if len({type(p) for p in parts}) == 1:
                return parts[0]._new(np.column_stack([p.flat()
                                                      for p in parts]))
        if any(isinstance(p, _Vec) for p in parts):
            raise MatlabError("Unable to concatenate datetime, duration and "
                              "numeric table variables.")
        if all(p.dtype == bool for p in parts):
            m = np.column_stack(parts)
        else:
            m = np.column_stack([p.astype(complex if np.iscomplexobj(p)
                                          else float) for p in parts])
        return _normalise(m)

    # assignment -----------------------------------------------------
    def _ml_assign(self, rt, kind, key, rest, value, owned=False):
        t = self.copy()
        if kind == ".":
            return t._assign_dot(rt, key, rest, value)
        if rest:
            raise MatlabError("A table element cannot be indexed further; "
                              "use T.Var(i) or T{i, j}.")
        if kind == "()":
            return t._assign_paren(rt, key, value)
        return t._assign_paren(rt, key, value, brace=True)

    def _set_var(self, name: str, col, desc: str = "") -> None:
        if name in self.columns:
            self._data[self.columns.index(name)] = col
            return
        if not self.columns and self._height == 0 and not self.row_names:
            self._height = len(col)
        if len(col) != self._height:
            raise MatlabError("To assign to or create a variable in a table, "
                              "the number of rows must match the height of "
                              "the table.")
        if self._descriptions or desc:
            self._descriptions = (self._descriptions or [""] * len(
                self.columns)) + [desc]
        self.columns.append(name)
        self._data.append(col)

    def _assign_dot(self, rt, key, rest, value):
        if key == "Properties":
            if not rest or rest[0][0] != ".":
                raise MatlabError("Assign to a table property such as "
                                  "T.Properties.VariableNames.")
            return self._set_property(rt, rest[0][1], rest[1:], value)
        if rest:
            if key not in self.columns:
                raise MatlabError(f"Unrecognized table variable name "
                                  f"'{key}'.")
            current = self.variable(self.columns.index(key))
            value = rt.assign(current, rest, value)
        elif isinstance(value, np.ndarray) and value.size == 0 and \
                self._height != 0:
            raise MatlabError("To assign to or create a variable in a table, "
                              "the number of rows must match the height of "
                              "the table.")
        if key in ("Row", ) and False:
            pass
        n = self._height if (self.columns or self._height) else None
        col = to_col(value, 1, n)
        self._set_var(key, col)
        return self

    def _set_property(self, rt, prop, rest, value):
        if rest:
            current = {"VariableNames": Cell(self.columns, rows=1),
                       "RowNames": Cell(self.row_names or [],
                                        rows=len(self.row_names or []))
                       }.get(prop)
            value = rt.assign(current, rest, value)
        if prop == "VariableNames":
            names = _name_cell(value, len(self.columns))
            if len(set(names)) != len(names):
                dup = next(n for n in names if names.count(n) > 1)
                raise MatlabError(f"Duplicate table variable name: '{dup}'.")
            if "Properties" in names:
                raise MatlabError("'Properties' is a reserved name.")
            self.columns = names
        elif prop == "RowNames":
            if isinstance(value, np.ndarray) and value.size == 0:
                self.row_names = None
            else:
                names = _name_cell(value, self._height, "RowNames")
                if len(set(names)) != len(names):
                    dup = next(n for n in names if names.count(n) > 1)
                    raise MatlabError(f"Duplicate row name: '{dup}'.")
                self.row_names = names
        elif prop == "Description":
            self.description = str(value)
        elif prop == "VariableDescriptions":
            self._descriptions = list(_name_cell(value, len(self.columns),
                                                 "VariableDescriptions"))
        else:
            raise MatlabError(f"Unrecognized table property '{prop}'.")
        return self

    # growing and deleting rows
    def grow_to(self, h: int) -> None:
        if h <= self._height:
            return
        extra = h - self._height
        self._data = [col_concat(c, col_blank(c, extra))
                      for c in self._data]
        if self.row_names:
            self.row_names = self.row_names + [
                f"Row{self._height + i + 1}" for i in range(extra)]
        self._height = h

    def delete_rows(self, rows) -> None:
        keep = [i for i in range(self._height) if i not in set(rows)]
        self._data = [col_take(c, keep) for c in self._data]
        if self.row_names:
            self.row_names = [self.row_names[i] for i in keep]
        self._height = len(keep)

    def delete_vars(self, ks) -> None:
        keep = [k for k in range(len(self.columns)) if k not in set(ks)]
        self._descriptions = ([self._descriptions[k] for k in keep]
                              if self._descriptions else [])
        self.columns = [self.columns[k] for k in keep]
        self._data = [self._data[k] for k in keep]

    def _row_targets(self, rt, arg):
        """Rows written to by ``T(arg, …) = v``: 0-based, may pass the end."""
        if _is_colon(arg):
            return list(range(self._height))
        if isinstance(arg, (str, Cell)):
            return self._row_indices(arg)
        r = np.asarray(rt._resolve(arg, self._height)
                       if hasattr(rt, "_resolve") else _mr._resolve(
                           arg, self._height))
        if r.dtype == bool:
            return np.nonzero(r.reshape(-1, order="F"))[0].tolist()
        r = r.reshape(-1)
        if r.size and (np.any(r < 1) or np.any(r != np.round(r))):
            raise MatlabError("Array indices must be positive integers.")
        return (r.astype(int) - 1).tolist()

    def _assign_paren(self, rt, key, value, brace=False):
        if len(key) != 2:
            raise MatlabError("Tables are two-dimensional: index as "
                              "t(rows, vars).")
        rows_arg, vars_arg = key
        empty = isinstance(value, np.ndarray) and value.size == 0
        if empty and not brace:
            if _is_colon(vars_arg):
                self.delete_rows(self._row_targets(rt, rows_arg))
            elif _is_colon(rows_arg):
                self.delete_vars(self._var_indices(vars_arg))
            else:
                raise MatlabError("To delete elements of a table, specify "
                                  "entire rows or entire variables, as in "
                                  "T(rows, :) = [] or T(:, vars) = [].")
            return self
        # variables (new names allowed when writing a whole column)
        new_names = []
        if isinstance(vars_arg, str) and vars_arg != ":" \
                and vars_arg not in self.columns:
            new_names, ks = [vars_arg], None
        elif isinstance(vars_arg, Cell) and any(
                v not in self.columns for v in vars_arg):
            new_names = [v for v in vars_arg if v not in self.columns]
            ks = None
        else:
            ks = self._var_indices(vars_arg)
        rows = self._row_targets(rt, rows_arg)
        if new_names:
            if len(new_names) != (len(vars_arg) if isinstance(
                    vars_arg, Cell) else 1):
                raise MatlabError("Cannot mix existing and new variables.")
            names = new_names
            cols = self._pieces(value, len(names), len(rows) or 1, brace)
            for nm, c in zip(names, cols):
                self._set_var(nm, to_col(c, 1, self._height)
                              if not isinstance(c, (list, np.ndarray, _Vec))
                              else c)
            return self
        if rows and max(rows) >= self._height:
            self.grow_to(max(rows) + 1)
        n_rows = len(rows)
        pieces = self._pieces(value, len(ks), n_rows, brace)
        for k, p in zip(ks, pieces):
            old = self._data[k]
            if isinstance(old, list) and isinstance(p, str):
                p = [p] * n_rows
            self._data[k] = col_set(old, rows, self._fit(p, n_rows))
        return self

    @staticmethod
    def _fit(p, n):
        if isinstance(p, np.ndarray) and p.size == 1 and n != 1:
            return np.repeat(p, n)
        if isinstance(p, list) and len(p) == 1 and n != 1:
            return p * n
        if isinstance(p, _Vec) and len(p) == 1 and n != 1:
            return p._new(np.repeat(p.flat(), n).reshape(-1, 1))
        return p

    def _pieces(self, value, nv: int, nr: int, brace: bool) -> list:
        """The right-hand side cut into one column per target variable."""
        if isinstance(value, ColumnTable):
            if len(value.columns) != nv:
                raise MatlabError("The right hand side of the assignment "
                                  "has the wrong number of variables.")
            if value.height not in (nr, 1):
                raise MatlabError("The right hand side of the assignment "
                                  "has the wrong number of rows.")
            return list(value._data)
        if isinstance(value, Cell):
            r, c = value.dims
            grid = value.grid() if len(value) else []
            if (r, c) == (1, 1) and (nv, nr) != (1, 1):
                grid, r, c = [[grid[0][0]] * nv for _ in range(nr)], nr, nv
            if (r, c) != (nr, nv):
                raise MatlabError("The right hand side of the assignment "
                                  "has the wrong size.")
            out = []
            for j in range(nv):
                col = [grid[i][j] for i in range(nr)]
                if all(isinstance(v, str) for v in col):
                    out.append(col)
                elif all(_mr._is_number(v) for v in col):
                    out.append(np.array(col, dtype=float))
                else:
                    raise MatlabError("Each cell column must be all text "
                                      "or all numbers.")
            return out
        if isinstance(value, str):
            return [[value] * nr for _ in range(nv)]
        if isinstance(value, _Vec):
            if nv != 1:
                raise MatlabError("A datetime or duration can fill one "
                                  "variable at a time.")
            return [value]
        a = _as_array(value)
        if a.ndim == 0 or a.size == 1:
            return [a.reshape(1).astype(a.dtype if a.dtype == bool else float)
                    for _ in range(nv)]
        a2 = a.reshape(1, -1) if a.ndim == 1 else a
        if a2.shape != (nr, nv):
            if a2.shape == (nv, nr) and 1 in (nv, nr):
                a2 = a2.T
            else:
                raise MatlabError(
                    f"Unable to perform assignment because the size of the "
                    f"left side is {nr}-by-{nv} and the size of the right "
                    f"side is {a2.shape[0]}-by-{a2.shape[1]}.")
        a2 = a2 if a2.dtype == bool else a2.astype(
            complex if np.iscomplexobj(a2) else float)
        return [a2[:, j].copy() for j in range(nv)]

    # display --------------------------------------------------------
    def _shown_columns(self):
        """[(header, texts, right-aligned)] for the display."""
        out = []
        if self.row_names:
            out.append(("", list(self.row_names), False))
        for name, col in zip(self.columns, self._data):
            texts, right = col_texts(col)
            out.append((name, texts, right))
        return out

    def __repr__(self) -> str:
        n, w = self.height, len(self.columns)
        if n == 0 or w == 0:
            return f"{n}×{w} empty {self.ml_class}"
        shown = self._shown_columns()
        widths = [max(len(h), *(len(t) for t in texts))
                  for h, texts, _ in shown]
        blocks, current, used = [], [], 0
        for k, wd in enumerate(widths):
            if current and used + wd + 4 > TABLE_WIDTH:
                blocks.append(current)
                current, used = [], 0
            current.append(k)
            used += wd + 4
        blocks.append(current)
        out = [f"{n}×{w} {self.ml_class}", ""]
        for b, block in enumerate(blocks):
            if b:
                out.append("")
            out.append("    " + "    ".join(
                shown[k][0].center(widths[k]) for k in block).rstrip())
            out.append("    " + "    ".join("_" * widths[k] for k in block))
            out.append("")
            for i in range(n):
                out.append("    " + "    ".join(
                    shown[k][1][i].rjust(widths[k]) if shown[k][2]
                    else shown[k][1][i].ljust(widths[k])
                    for k in block).rstrip())
        return "\n".join(out)

    # helpers for the library ---------------------------------------
    def column_index(self, name) -> int:
        if isinstance(name, str):
            if name not in self.columns:
                raise MatlabError(f"Unrecognized table variable name "
                                  f"'{name}'.")
            return self.columns.index(name)
        return int(name) - 1

    def row_keys(self, ks) -> list[tuple]:
        keys = [col_keys(self._data[k]) for k in ks]
        return [tuple(c[i] for c in keys) for i in range(self._height)]


def _name_cell(value, n: int, what: str = "VariableNames") -> list[str]:
    names = [value] if isinstance(value, str) else list(value) \
        if isinstance(value, (Cell, list)) else None
    if names is None or not all(isinstance(x, str) for x in names):
        raise MatlabError(f"'{what}' must be a cell array of char vectors.")
    if len(names) != n:
        raise MatlabError(f"The {what} property must contain one name "
                          f"for each {'row' if what == 'RowNames' else 'variable'}"
                          f" in the table ({n}).")
    return names


# ──────────────────────────────────────────────────────────────
#  The timetable
# ──────────────────────────────────────────────────────────────

class Timetable(ColumnTable):
    ml_class = "timetable"

    def __init__(self, names, data, time: _Vec, time_name="Time",
                 descriptions=None, height=None) -> None:
        super().__init__(names, data, descriptions, height=len(time))
        if time_name in self.columns:
            raise MatlabError(f"The row-times name '{time_name}' is also a "
                              f"variable name.")
        self.time = time._new(time.flat().reshape(-1, 1))
        self.time_name = time_name
        self._height = len(time)
        if data and len(data[0]) != self._height:
            raise MatlabError("The row times must have one entry per row of "
                              "data.")

    def _like(self, names, data, desc=None, height=None, row_names=None,
              time=None):
        t = Timetable(names, data, time if time is not None else self.time,
                      self.time_name, desc, height)
        t.description = self.description
        return t

    def select(self, rows, ks):
        data = [col_take(self._data[k], rows) for k in ks]
        desc = ([self._descriptions[k] for k in ks]
                if self._descriptions else [])
        return self._like([self.columns[k] for k in ks], data, desc,
                          len(rows), None, self.time.take(rows))

    def __getattr__(self, name: str):
        if name == self.__dict__.get("time_name", "\0"):
            return self.time
        return super().__getattr__(name)

    def properties(self) -> Struct:
        p = super().properties()
        p["RowTimes"] = self.time
        p["DimensionNames"] = Cell([self.time_name, "Variables"], rows=1)
        p["RowNames"] = Cell()
        return p

    def _row_indices(self, arg) -> list[int]:
        if isinstance(arg, TimeRange):
            return np.nonzero(arg.mask(self.time))[0].tolist()
        if isinstance(arg, Datetime) or (isinstance(arg, Cell) and len(arg)
                                         and False):
            keys = self.time.keys()
            out = []
            for k in arg.keys():
                hit = np.nonzero(keys == k)[0]
                if not hit.size:
                    raise MatlabError("Unrecognized row time in the "
                                      "timetable subscript.")
                out.extend(hit.tolist())
            return out
        if isinstance(arg, Duration):
            keys = self.time.keys()
            out = []
            for k in arg.keys():
                hit = np.nonzero(keys == k)[0]
                if not hit.size:
                    raise MatlabError("Unrecognized row time in the "
                                      "timetable subscript.")
                out.extend(hit.tolist())
            return out
        return _positions(arg, self.height)

    def grow_to(self, h: int) -> None:
        if h > self._height:
            raise MatlabError("A timetable cannot grow by assigning past "
                              "its last row; append with [TT1; TT2].")

    def delete_rows(self, rows) -> None:
        keep = [i for i in range(self._height) if i not in set(rows)]
        self.time = self.time.take(keep)
        super().delete_rows(rows)

    def _set_property(self, rt, prop, rest, value):
        if prop == "RowTimes":
            if not isinstance(value, _Vec) or len(value) != self._height:
                raise MatlabError("RowTimes must be a datetime or duration "
                                  "vector with one entry per row.")
            self.time = value._new(value.flat().reshape(-1, 1))
            return self
        if prop == "DimensionNames":
            names = _name_cell(value, 2, "DimensionNames")
            self.time_name = names[0]
            return self
        return super()._set_property(rt, prop, rest, value)

    def _assign_dot(self, rt, key, rest, value):
        if key == self.time_name and not rest:
            return self._set_property(rt, "RowTimes", [], value)
        return super()._assign_dot(rt, key, rest, value)

    def _shown_columns(self):
        texts = self.time.texts()
        out = [(self.time_name, texts, True)]
        for name, col in zip(self.columns, self._data):
            t, right = col_texts(col)
            out.append((name, t, right))
        return out

    def to_table(self) -> ColumnTable:
        return ColumnTable([self.time_name] + self.columns,
                           [self.time] + self._data,
                           ([""] + self._descriptions)
                           if self._descriptions else [], self._height)


__all__ = ["ColumnTable", "Timetable", "TimeRange", "col_take", "col_set",
           "col_concat", "col_keys", "col_value", "col_texts", "to_col",
           "short_g"]
