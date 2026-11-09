"""
Table functions.
================
``table`` and everything that takes one: ``sortrows``, ``join``,
``groupsummary``, ``varfun``, ``timetable``, ``fitlm`` … A mixin of
:class:`.matlab_runtime._Library`; the table itself is in :mod:`.tables`.

:func:`install_dispatch` lets the older builtins (``sort``, ``min``,
``diff``, ``unique`` …) answer for a datetime, duration or table: when
the first argument has an ``ml_<name>`` method, that method is called.
"""

from __future__ import annotations

import functools

import numpy as np

from . import matlab_runtime as _mr  # noqa: F401
from .lib_dates import DISPATCHED, Datetime, Duration, _Vec
from .matlab_runtime import (
    Cell,
    MatlabError,
    Struct,
    StructArray,
    Table,
    _as2d,
    _as_array,
    _is_number,
    _named,
    _nargout,
    _normalise,
    _shape,
)
from .tables import (
    ColumnTable,
    TimeRange,
    Timetable,
    _name_cell,
    col_concat,
    col_keys,
    col_take,
    col_value,
    to_col,
)

_TABLE_OPTS = ("variablenames", "rownames", "size", "variabletypes")


def _opts(args, allowed: dict, fn: str) -> dict:
    if len(args) % 2:
        raise MatlabError(f"{fn}: options must come in name-value pairs.")
    out = {}
    for k, v in zip(args[0::2], args[1::2]):
        key = str(k).lower()
        if key not in allowed:
            raise MatlabError(f"{fn}: the '{k}' option is not supported in "
                              f"Evans.")
        out[allowed[key]] = v
    return out


def _need_table(T, fn):
    if not isinstance(T, ColumnTable):
        raise MatlabError(f"{fn} needs a table.")
    return T


def _names(v) -> list[str]:
    return [v] if isinstance(v, str) else list(v)


def _dense_rank(keys: list) -> np.ndarray:
    uniq = sorted(set(keys))
    pos = {k: i for i, k in enumerate(uniq)}
    return np.array([pos[k] for k in keys], dtype=int)


def _sort_order(columns: list, descending: list[bool]) -> np.ndarray:
    """Stable row order for several key columns (missing last, or first
    when descending, as MATLAB does)."""
    n = len(columns[0]) if columns else 0
    order = np.arange(n)
    for keys, desc in reversed(list(zip((col_keys(c) for c in columns),
                                        descending))):
        r = _dense_rank(keys)
        if desc:
            r = -r
        order = order[np.argsort(r[order], kind="stable")]
    return order


def _directions(direction, n: int) -> list[bool]:
    if direction is None:
        return [False] * n
    ds = _names(direction)
    if len(ds) == 1:
        ds = ds * n
    if len(ds) != n or any(str(d).lower() not in ("ascend", "descend")
                           for d in ds):
        raise MatlabError("sortrows: direction must be 'ascend' or "
                          "'descend', one per sorting column.")
    return [str(d).lower() == "descend" for d in ds]


def concat_objects(rows: list[list]):
    """``[a, b; c, d]`` where an element is a table or datetime/duration."""
    flat = [x for r in rows for x in r]
    if any(isinstance(x, ColumnTable) for x in flat):
        stacked = []
        for r in rows:
            acc = r[0]
            for x in r[1:]:
                acc = _hcat(acc, x)
            stacked.append(acc)
        acc = stacked[0]
        for x in stacked[1:]:
            acc = _vcat(acc, x)
        return acc
    if any(isinstance(x, _Vec) for x in flat):
        kind = type(next(x for x in flat if isinstance(x, _Vec)))
        if not all(isinstance(x, kind) for x in flat):
            raise MatlabError("Cannot concatenate a datetime or duration "
                              "with another type.")
        blocks = [np.hstack([x.a for x in r]) for r in rows]
        first = flat[0]
        return kind(np.vstack(blocks), first.fmt)
    raise MatlabError("Unsupported concatenation.")


def _hcat(a, b):
    if not (isinstance(a, ColumnTable) and isinstance(b, ColumnTable)):
        raise MatlabError("A table can only be concatenated with tables.")
    if a.height != b.height:
        raise MatlabError("Dimensions of the tables being horizontally "
                          "concatenated are not consistent.")
    t = a.copy()
    for n, c in zip(b.columns, b._data):
        t._set_var(n, c)
    return t


def _vcat(a, b):
    if not (isinstance(a, ColumnTable) and isinstance(b, ColumnTable)):
        raise MatlabError("A table can only be concatenated with tables.")
    if sorted(a.columns) != sorted(b.columns):
        raise MatlabError("Vertical concatenation of tables needs the same "
                          "variable names in both.")
    data = [col_concat(c, b._data[b.columns.index(n)])
            for n, c in zip(a.columns, a._data)]
    if isinstance(a, Timetable) and isinstance(b, Timetable):
        time = a.time._new(np.concatenate([a.time.flat(), b.time.flat()])
                           .reshape(-1, 1))
        return Timetable(a.columns, data, time, a.time_name)
    rn = (a.row_names + b.row_names) if a.row_names and b.row_names else None
    return ColumnTable(a.columns, data, a._descriptions,
                       a.height + b.height, rn)


def _call_fn(rt, fn, args):
    return rt.call(fn, tuple(args), nargout=1)


class _GroupInfo:
    def __init__(self, T: ColumnTable, gvars: list[int]):
        keys = T.row_keys(gvars)
        self.ids = sorted(set(keys))
        pos = {k: i for i, k in enumerate(self.ids)}
        self.index = [[] for _ in self.ids]
        for r, k in enumerate(keys):
            self.index[pos[k]].append(r)
        self.first = [ix[0] for ix in self.index]


def _scalar_col(values: list):
    if all(isinstance(v, str) for v in values):
        return list(values)
    if all(isinstance(v, (_Vec)) for v in values):
        return values[0]._new(np.concatenate([v.flat() for v in values])
                              .reshape(-1, 1))
    arr = []
    for v in values:
        a = _as_array(v)
        if a.size != 1:
            raise MatlabError("The function must return a scalar for each "
                              "group or row.")
        arr.append(a.reshape(-1)[0])
    out = np.array(arr)
    return out.astype(bool) if out.dtype == bool else out.astype(float)


_STATS = {
    "mean": np.nanmean, "sum": np.nansum, "min": np.nanmin,
    "max": np.nanmax, "median": np.nanmedian,
    "std": lambda x: np.nanstd(x, ddof=1) if len(x) > 1 else 0.0,
    "var": lambda x: np.nanvar(x, ddof=1) if len(x) > 1 else 0.0,
    "range": lambda x: np.nanmax(x) - np.nanmin(x),
    "nnz": lambda x: float(np.count_nonzero(x)),
    "numunique": lambda x: float(len(set(x.tolist()))),
    "nummissing": lambda x: float(np.isnan(x).sum()),
    "mode": lambda x: min(v for v in set(x.tolist())
                          if x.tolist().count(v) == max(
                              x.tolist().count(u) for u in set(x.tolist()))),
}


class TableLibrary:
    """Mixed into the runtime's function library."""

    # ── making tables ──────────────────────────────────────────

    @_named
    def f_table(self, *args, names=None):
        names = list(names or [])
        values, opts = [], []
        for k, a in enumerate(args):
            if isinstance(a, str) and a.lower() in _TABLE_OPTS:
                opts = list(args[k:])
                break
            values.append(a)
        given = _opts(opts, {"variablenames": "VariableNames",
                             "rownames": "RowNames", "size": "Size",
                             "variabletypes": "VariableTypes"}, "table")
        if "Size" in given:
            size = _as_array(given["Size"]).reshape(-1)
            types = _names(given.get("VariableTypes", ["double"] * int(
                size[1])))
            n = int(size[0])
            mk = {"double": lambda: np.full(n, np.nan),
                  "logical": lambda: np.zeros(n, bool),
                  "cell": lambda: [""] * n, "string": lambda: [""] * n,
                  "char": lambda: [""] * n,
                  "datetime": lambda: Datetime.blank(n),
                  "duration": lambda: Duration.blank(n)}
            try:
                data = [mk[str(t)]() for t in types]
            except KeyError as e:
                raise MatlabError(f"table: variable type {e} is not "
                                  f"supported.") from None
            nm = (_name_cell(given["VariableNames"], len(data))
                  if "VariableNames" in given else
                  [f"Var{k + 1}" for k in range(len(data))])
            return ColumnTable(nm, data, height=n)
        if "VariableNames" in given:
            var_names = _name_cell(given["VariableNames"], len(values))
        else:
            var_names = [names[k] if k < len(names) and names[k]
                         else f"Var{k + 1}" for k in range(len(values))]
        data = [to_col(v, k + 1) for k, v in enumerate(values)]
        rn = None
        if "RowNames" in given:
            h = len(data[0]) if data else 0
            rn = _name_cell(given["RowNames"], h, "RowNames")
        return ColumnTable(var_names, data, row_names=rn)

    def f_array2table(self, A, *args):
        given = _opts(args, {"variablenames": "VariableNames",
                             "rownames": "RowNames"}, "array2table")
        if isinstance(A, Cell):
            r, c = A.dims
            grid = A.grid()
            data = []
            for j in range(c):
                col = [grid[i][j] for i in range(r)]
                if all(isinstance(v, str) for v in col):
                    data.append(col)
                elif all(_is_number(v) for v in col):
                    data.append(np.array(col, dtype=float))
                else:
                    raise MatlabError("array2table: Evans needs each cell "
                                      "column to be all text or all "
                                      "numbers.")
            height = r
        else:
            if isinstance(A, (str, Struct, StructArray, Table)):
                raise MatlabError("array2table needs a numeric, logical or "
                                  "cell matrix.")
            a = _as2d(_as_array(A))
            if a.dtype != bool:
                a = a.astype(complex if np.iscomplexobj(a) else float)
            data = [a[:, j].copy() for j in range(a.shape[1])]
            height = a.shape[0]
        n = len(data)
        var_names = (_name_cell(given["VariableNames"], n)
                     if "VariableNames" in given
                     else [f"Var{k + 1}" for k in range(n)])
        rn = (_name_cell(given["RowNames"], height, "RowNames")
              if "RowNames" in given else None)
        return ColumnTable(var_names, data, height=height, row_names=rn)

    def f_table2array(self, T):
        _need_table(T, "table2array")
        if not T.columns:
            return np.zeros((T.height, 0))
        return T._concat_vars(list(range(T.height)),
                              list(range(len(T.columns))))

    def f_table2cell(self, T):
        _need_table(T, "table2cell")
        grid = [[(c[i] if isinstance(c, list) else
                  c.take([i]) if isinstance(c, _Vec) else
                  _mr._scalar(c[i].item() if hasattr(c[i], "item") else c[i]))
                 for c in T._data] for i in range(T.height)]
        return Cell.from_grid(grid) if grid else Cell()

    def f_cell2table(self, C, *args):
        return self.f_array2table(C, *args)

    def f_table2struct(self, T, *args):
        _need_table(T, "table2struct")
        rows = [Struct({n: (c[i] if isinstance(c, list) else
                            _mr._scalar(c[i].item()) if isinstance(
                                c, np.ndarray) else c.take([i]))
                        for n, c in zip(T.columns, T._data)})
                for i in range(T.height)]
        if args and str(args[0]).lower() == "toscalar":
            return Struct({n: col_value(c) for n, c in zip(T.columns,
                                                           T._data)})
        return StructArray(rows, rows=len(rows)) if len(rows) != 1 \
            else rows[0]

    def f_height(self, T):
        return _shape(T)[0]

    def f_width(self, T):
        return _shape(T)[1]

    def f_istable(self, x):
        return isinstance(x, ColumnTable)

    def f_istimetable(self, x):
        return isinstance(x, Timetable)

    # ── variables ──────────────────────────────────────────────

    def f_removevars(self, T, vars_):
        _need_table(T, "removevars")
        t = T.copy()
        t.delete_vars(T._var_indices(vars_))
        return t

    def f_addvars(self, T, *args):
        _need_table(T, "addvars")
        values, k = [], 0
        while k < len(args) and not (isinstance(args[k], str) and
                                     args[k].lower() in (
                                         "before", "after",
                                         "newvariablenames")):
            values.append(args[k])
            k += 1
        o = _opts(args[k:], {"before": "before", "after": "after",
                             "newvariablenames": "names"}, "addvars")
        t = T.copy()
        new = (_names(o["names"]) if "names" in o else
               [f"Var{len(T.columns) + i + 1}" for i in range(len(values))])
        for n, v in zip(new, values):
            t._set_var(n, to_col(v, 1, T.height))
        anchor = o.get("before", o.get("after"))
        if anchor is not None:
            a = T.column_index(anchor)
            pos = a if "before" in o else a + 1
            order = (list(range(pos)) +
                     list(range(len(T.columns), len(t.columns))) +
                     list(range(pos, len(T.columns))))
            t = t.select(list(range(t.height)), order)
        return t

    def f_renamevars(self, T, old, new):
        _need_table(T, "renamevars")
        t = T.copy()
        ks = T._var_indices(old)
        nn = _names(new)
        if len(nn) != len(ks):
            raise MatlabError("renamevars: give one new name per variable.")
        for k, n in zip(ks, nn):
            t.columns[k] = n
        return t._set_property(None, "VariableNames", [], Cell(
            t.columns, rows=1))

    def f_movevars(self, T, vars_, where, ref):
        _need_table(T, "movevars")
        ks = T._var_indices(vars_)
        rest = [k for k in range(len(T.columns)) if k not in ks]
        r = T.column_index(ref)
        if r in ks:
            raise MatlabError("movevars: the reference variable cannot be "
                              "one of those moved.")
        at = rest.index(r) + (0 if str(where).lower() == "before" else 1)
        return T.select(list(range(T.height)), rest[:at] + ks + rest[at:])

    # ── looking at tables ──────────────────────────────────────

    def f_head(self, T, k=8):
        return self._headtail(T, int(k), True)

    def f_tail(self, T, k=8):
        return self._headtail(T, int(k), False)

    def _headtail(self, T, k, head):
        if isinstance(T, ColumnTable):
            n = T.height
            rows = list(range(min(k, n))) if head else \
                list(range(max(n - k, 0), n))
            return T.select(rows, list(range(len(T.columns))))
        a = _as2d(_as_array(T))
        n = a.shape[0]
        out = a[:k] if head else a[max(n - k, 0):]
        return _normalise(out)

    def f_summary(self, T):
        _need_table(T, "summary")
        lines = ["Variables:", ""]
        for n, c in zip(T.columns, T._data):
            h = T.height
            if isinstance(c, list):
                lines += [f"    {n}: {h}×1 cell array of character vectors",
                          ""]
            elif isinstance(c, _Vec):
                lines += [f"    {n}: {h}×1 {c.ml_class}", ""]
            elif c.dtype == bool:
                lines += [f"    {n}: {h}×1 logical", "",
                          "        True    " + str(int(c.sum())),
                          "        False   " + str(int((~c).sum())), ""]
            else:
                r = c.real if np.iscomplexobj(c) else c
                nm = int(np.isnan(r).sum())
                lines += [f"    {n}: {h}×1 double", "", "        Values:",
                          "",
                          f"            Min          {np.nanmin(r):.5g}",
                          f"            Median       {np.nanmedian(r):.5g}",
                          f"            Max          {np.nanmax(r):.5g}",
                          f"            NumMissing   {nm}", ""]
        print("\n".join(lines))

    # ── sorting and sets ───────────────────────────────────────

    @_nargout
    def f_sortrows(self, A, *args, nargout=1):
        cols = direction = None
        if args:
            cols = args[0]
            direction = args[1] if len(args) > 1 else None
        if isinstance(A, ColumnTable):
            return A.ml_sortrows(self, cols, direction, nargout=nargout)
        if isinstance(A, Cell):
            vals = list(A)
            if not all(isinstance(v, str) for v in vals):
                raise MatlabError("sortrows of a cell array needs text.")
            order = _sort_order([vals], _directions(direction, 1))
            out = Cell([vals[i] for i in order], rows=A.dims[0])
            return (out, (order + 1.0).reshape(-1, 1)) if nargout > 1 else out
        a = _as2d(_as_array(A))
        if cols is None:
            ks = list(range(1, a.shape[1] + 1))
        else:
            ks = [int(x) for x in _as_array(cols).reshape(-1)]
        desc = [k < 0 for k in ks]
        if direction is not None:
            desc = _directions(direction, len(ks))
        order = _sort_order([a[:, abs(k) - 1] for k in ks], desc)
        out = _normalise(a[order])
        return (out, (order + 1.0).reshape(-1, 1)) if nargout > 1 else out

    # ── joins ──────────────────────────────────────────────────

    @_nargout
    def f_innerjoin(self, A, B, *args, nargout=1):
        out, il, ir = self._join(A, B, args, "innerjoin")
        return (out, il, ir) if nargout > 1 else out

    @_nargout
    def f_outerjoin(self, A, B, *args, nargout=1):
        out, il, ir = self._join(A, B, args, "outerjoin")
        return (out, il, ir) if nargout > 1 else out

    def _join(self, A, B, args, kind):
        _need_table(A, kind)
        _need_table(B, kind)
        o = _opts(args, {"keys": "keys", "leftkeys": "lk",
                         "rightkeys": "rk", "type": "type",
                         "mergekeys": "merge",
                         "leftvariables": "lv", "rightvariables": "rv"},
                  kind)
        if "keys" in o:
            lk = rk = _names(o["keys"])
        elif "lk" in o:
            lk, rk = _names(o["lk"]), _names(o["rk"])
        else:
            lk = rk = [n for n in A.columns if n in B.columns]
            if not lk:
                raise MatlabError(f"{kind}: the tables have no variable "
                                  f"names in common; give 'Keys'.")
        kind_t = str(o.get("type", "full")).lower() if kind == "outerjoin" \
            else "inner" if kind == "innerjoin" else "left"
        ia = [A.column_index(n) for n in lk]
        ib = [B.column_index(n) for n in rk]
        ka, kb = A.row_keys(ia), B.row_keys(ib)
        if kind == "join":
            if len(set(kb)) != len(kb):
                raise MatlabError("join: the key values in the second "
                                  "table must be unique.")
            if any(k not in set(kb) for k in ka):
                raise MatlabError("join: every key value in the first "
                                  "table must appear in the second.")
        by_b = {}
        for j, k in enumerate(kb):
            by_b.setdefault(k, []).append(j)
        pairs = []                       # (i or None, j or None)
        for i, k in enumerate(ka):
            for j in by_b.get(k, []) or ([None] if kind_t in (
                    "left", "full") else []):
                pairs.append((i, j))
        if kind_t in ("right", "full"):
            seen = set(ka)
            pairs += [(None, j) for j, k in enumerate(kb) if k not in seen]
        if kind != "join":
            def sortkey(p):
                k = ka[p[0]] if p[0] is not None else kb[p[1]]
                return (k, p[0] if p[0] is not None else -1,
                        p[1] if p[1] is not None else -1)
            pairs.sort(key=sortkey)
        names, data = [], []
        merge = bool(o.get("merge", False)) or kind in ("join", "innerjoin")
        left_rest = [k for k in range(len(A.columns)) if k not in ia]
        right_rest = [k for k in range(len(B.columns)) if k not in ib]

        def pick(col, idxs):
            miss = [i is None for i in idxs]
            real = [0 if m else i for m, i in zip(miss, idxs)]
            out = col_take(col, real) if len(col) else col
            if any(miss):
                from .tables import col_blank, col_set
                out = col_set(out, [r for r, m in enumerate(miss) if m],
                              col_blank(out, sum(miss)))
            return out

        li = [p[0] for p in pairs]
        ri = [p[1] for p in pairs]
        for a, b, name in zip(ia, ib, lk):
            col = pick(A._data[a], li)
            if merge and any(i is None for i in li):
                from .tables import col_set
                fill = [r for r, i in enumerate(li) if i is None]
                col = col_set(col, fill, col_take(B._data[b],
                                                  [ri[r] for r in fill]))
            if merge:
                names.append(name)
                data.append(col)
            else:
                names.append(name + "_left")
                data.append(col)
                names.append(rk[ia.index(a)] + "_right")
                data.append(pick(B._data[b], ri))
        other = {A.columns[k] for k in left_rest} & \
            {B.columns[k] for k in right_rest}
        for k in left_rest:
            n = A.columns[k]
            names.append(n + "_left" if n in other else n)
            data.append(pick(A._data[k], li))
        for k in right_rest:
            n = B.columns[k]
            names.append(n + "_right" if n in other else n)
            data.append(pick(B._data[k], ri))
        out = ColumnTable(names, data, height=len(pairs))
        return (out, np.array([[(0 if i is None else i + 1)]
                               for i in li], float).reshape(-1, 1),
                np.array([[(0 if j is None else j + 1)]
                          for j in ri], float).reshape(-1, 1))

    # ── grouping ───────────────────────────────────────────────

    @_nargout
    def f_findgroups(self, g, nargout=1):
        if isinstance(g, ColumnTable):
            gi = _GroupInfo(g, list(range(len(g.columns))))
        else:
            T = ColumnTable(["g"], [to_col(g, 1)])
            gi = _GroupInfo(T, [0])
        ids = np.empty(sum(len(ix) for ix in gi.index))
        for n, ix in enumerate(gi.index):
            ids[ix] = n + 1
        out = _normalise(ids.reshape(-1, 1))
        if nargout > 1:
            first = gi.first
            src = g if not isinstance(g, ColumnTable) else None
            return out, (col_value(col_take(to_col(src, 1), first))
                         if src is not None else None)
        return out

    def f_splitapply(self, fn, X, G):
        g = _as_array(G).reshape(-1).astype(int)
        cols = X if isinstance(X, ColumnTable) else None
        out = []
        for n in range(1, g.max() + 1 if g.size else 1):
            idx = np.nonzero(g == n)[0]
            if cols is not None:
                args = [col_value(col_take(c, idx)) for c in cols._data]
            else:
                a = _as_array(X).reshape(g.size, -1)
                args = [_normalise(a[idx])]
            out.append(_call_fn(self.rt, fn, args))
        return _normalise(_scalar_col(out).reshape(-1, 1)) \
            if not isinstance(_scalar_col(out), list) else Cell(
                _scalar_col(out), rows=len(out))

    def f_groupsummary(self, T, groupvars, method=None, datavars=None):
        _need_table(T, "groupsummary")
        gv = T._var_indices(groupvars)
        gi = _GroupInfo(T, gv)
        names = [T.columns[k] for k in gv]
        data = [col_take(T._data[k], gi.first) for k in gv]
        names.append("GroupCount")
        data.append(np.array([len(ix) for ix in gi.index], float))
        if method is not None:
            methods = _names(method) if not callable(method) else [method]
            dv = (T._var_indices(datavars) if datavars is not None else
                  [k for k in range(len(T.columns)) if k not in gv and
                   isinstance(T._data[k], np.ndarray)])
            for m in methods:
                for k in dv:
                    col = T._data[k]
                    vals = []
                    for ix in gi.index:
                        x = col[ix].astype(float)
                        if callable(m):
                            vals.append(_call_fn(self.rt, m,
                                                 [col_value(col_take(
                                                     col, ix))]))
                        elif m in _STATS:
                            vals.append(float(_STATS[m](x)))
                        else:
                            raise MatlabError(f"groupsummary: method '{m}' "
                                              f"is not supported.")
                    names.append(f"{m if isinstance(m, str) else 'fun'}_"
                                 f"{T.columns[k]}")
                    data.append(_scalar_col(vals))
        return ColumnTable(names, data, height=len(gi.ids))

    def f_varfun(self, fn, T, *args):
        _need_table(T, "varfun")
        o = _opts(args, {"inputvariables": "iv", "groupingvariables": "gv",
                         "outputformat": "fmt"}, "varfun")
        iv = T._var_indices(o["iv"]) if "iv" in o else \
            [k for k in range(len(T.columns))
             if k not in (T._var_indices(o["gv"]) if "gv" in o else [])]
        fname = getattr(fn, "__name__", "") or "Fun"
        fname = fname[2:] if fname.startswith("f_") else fname
        if not fname.isidentifier() or fname in ("lambda", "_anon")                 or fname.startswith("_"):
            fname = "Fun"
        gv = T._var_indices(o["gv"]) if "gv" in o else []
        fmt = str(o.get("fmt", "table")).lower()
        if gv:
            gi = _GroupInfo(T, gv)
            groups = gi.index
        else:
            groups = [list(range(T.height))]
        names = [T.columns[k] for k in gv]
        data = [col_take(T._data[k], [ix[0] for ix in groups])
                for k in gv]
        if gv:
            names.append("GroupCount")
            data.append(np.array([len(ix) for ix in groups], float))
        outs = []
        for k in iv:
            vals = [_call_fn(self.rt, fn, [col_value(col_take(T._data[k],
                                                              ix))])
                    for ix in groups]
            outs.append(_scalar_col(vals))
            names.append(f"{fname}_{T.columns[k]}")
            data.append(outs[-1])
        if fmt == "uniform":
            return _normalise(np.column_stack([np.asarray(o_, float)
                                               for o_ in outs]))
        if fmt == "cell":
            return Cell([col_value(o_) for o_ in outs], rows=1)
        return ColumnTable(names, data, height=len(groups))

    def f_rowfun(self, fn, T, *args):
        _need_table(T, "rowfun")
        o = _opts(args, {"inputvariables": "iv", "groupingvariables": "gv",
                         "outputvariablenames": "ov",
                         "outputformat": "fmt"}, "rowfun")
        gv = T._var_indices(o["gv"]) if "gv" in o else []
        iv = T._var_indices(o["iv"]) if "iv" in o else \
            [k for k in range(len(T.columns)) if k not in gv]
        ov = _names(o["ov"]) if "ov" in o else ["Var1"]
        if gv:
            gi = _GroupInfo(T, gv)
            groups = gi.index
        else:
            groups = [[i] for i in range(T.height)]
        vals = [_call_fn(self.rt, fn, [col_value(col_take(T._data[k], ix))
                                       if gv else
                                       _mr._scalar(_one(T._data[k], ix[0]))
                                       for k in iv]) for ix in groups]
        names = [T.columns[k] for k in gv]
        data = [col_take(T._data[k], [ix[0] for ix in groups]) for k in gv]
        if gv:
            names.append("GroupCount")
            data.append(np.array([len(ix) for ix in groups], float))
        names += ov[:1]
        data.append(_scalar_col(vals))
        if str(o.get("fmt", "table")).lower() == "uniform":
            return _normalise(np.asarray(data[-1], float).reshape(-1, 1))
        return ColumnTable(names, data, height=len(groups))

    # ── timetables ─────────────────────────────────────────────

    @_named
    def f_timetable(self, *args, names=None):
        names = list(names or [])
        if not args:
            raise MatlabError("timetable needs row times and data.")
        values, opts = [], []
        for k, a in enumerate(args):
            if isinstance(a, str) and a.lower() in (
                    "variablenames", "rowtimes", "timestep", "samplerate",
                    "starttime"):
                opts = list(args[k:])
                break
            values.append(a)
        given = _opts(opts, {"variablenames": "VariableNames",
                             "rowtimes": "RowTimes", "timestep": "TimeStep",
                             "starttime": "StartTime"}, "timetable")
        if "RowTimes" in given:
            time = given["RowTimes"]
        elif "TimeStep" in given:
            n = len(to_col(values[0], 1)) if values else 0
            start = given.get("StartTime", Duration(np.array([[0.0]])))
            time = start + Duration(np.arange(n, dtype=float).reshape(-1, 1)
                                    * given["TimeStep"].a)
        else:
            time, values = values[0], values[1:]
            names = names[1:]
        if not isinstance(time, _Vec):
            raise MatlabError("timetable: row times must be a datetime or "
                              "duration vector.")
        data = [to_col(v, k + 2) for k, v in enumerate(values)]
        nm = (_name_cell(given["VariableNames"], len(data))
              if "VariableNames" in given else
              [names[k] if k < len(names) and names[k] else f"Var{k + 1}"
               for k in range(len(data))])
        return Timetable(nm, data, time)

    def f_array2timetable(self, A, *args):
        o = _opts(args, {"rowtimes": "rt", "variablenames": "vn"},
                  "array2timetable")
        if "rt" not in o:
            raise MatlabError("array2timetable needs 'RowTimes'.")
        t = self.f_array2table(A, *(["VariableNames", o["vn"]]
                                    if "vn" in o else []))
        return Timetable(t.columns, t._data, o["rt"])

    def f_table2timetable(self, T, *args):
        _need_table(T, "table2timetable")
        ks = [k for k, c in enumerate(T._data) if isinstance(c, _Vec)]
        if not ks:
            raise MatlabError("table2timetable needs a datetime or "
                              "duration variable for the row times.")
        k = ks[0]
        rest = [j for j in range(len(T.columns)) if j != k]
        return Timetable([T.columns[j] for j in rest],
                         [T._data[j] for j in rest], T._data[k],
                         T.columns[k])

    def f_timetable2table(self, TT, *args):
        if not isinstance(TT, Timetable):
            raise MatlabError("timetable2table needs a timetable.")
        return TT.to_table()

    def f_timerange(self, lo, hi, interval="openright"):
        return TimeRange(lo, hi, str(interval).lower())

    # ── a linear model ─────────────────────────────────────────

    def f_fitlm(self, X, y=None, *args):
        return _fit(X, y, args)

    def f_predict(self, mdl, Xnew):
        if not isinstance(mdl, LinearModel):
            raise MatlabError("predict needs a model from fitlm.")
        return mdl.predict(Xnew)


def _one(col, i):
    v = col[i]
    return v.item() if hasattr(v, "item") else v


def _ml_sortrows(self, lib, cols=None, direction=None, nargout=1):
    if cols is None:
        ks = list(range(len(self.columns)))
        desc = _directions(direction, len(ks))
    else:
        items = _names(cols) if isinstance(cols, (str, Cell)) else [
            int(x) for x in _as_array(cols).reshape(-1)]
        ks, desc = [], []
        for it in items:
            if isinstance(it, str):
                ks.append(self.column_index(it))
                desc.append(False)
            else:
                ks.append(abs(it) - 1)
                desc.append(it < 0)
        if direction is not None:
            desc = _directions(direction, len(ks))
    if isinstance(self, Timetable) and not (cols is not None):
        order = _sort_order([self.time], [desc[0]] if desc else [False])
    else:
        order = _sort_order([self._data[k] for k in ks], desc)
    out = self.select(order.tolist(), list(range(len(self.columns))))
    if self.row_names:
        out.row_names = [self.row_names[i] for i in order]
    return (out, (order + 1.0).reshape(-1, 1)) if nargout > 1 else out


def _ml_unique(self, lib, *flags, nargout=1):
    stable = any(isinstance(f, str) and f.lower() == "stable" for f in flags)
    keys = self.row_keys(list(range(len(self.columns))))
    first = {}
    for i, k in enumerate(keys):
        first.setdefault(k, i)
    order = list(first.values()) if stable else sorted(
        first.values(), key=lambda i: keys[i])
    out = self.select(order, list(range(len(self.columns))))
    ia = np.array(order, float).reshape(-1, 1) + 1
    pos = {keys[i]: n for n, i in enumerate(order)}
    ic = np.array([pos[k] + 1 for k in keys], float).reshape(-1, 1)
    return (out, ia, ic) if nargout > 1 else out


def _ml_isequal(self, lib, *others):
    for o in others:
        if not isinstance(o, ColumnTable) or o.columns != self.columns \
                or o.height != self.height:
            return False
        for a, b in zip(self._data, o._data):
            if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
                if not np.array_equal(a, b):
                    return False
            elif isinstance(a, list) and isinstance(b, list):
                if a != b:
                    return False
            elif isinstance(a, _Vec) and isinstance(b, _Vec):
                if not a.ml_isequal(lib, b):
                    return False
            else:
                return False
    return True


def _ml_join(self, lib, B, *args, nargout=1):
    return lib._join(self, B, args, "join")[0]


def _ml_head(self, lib, k=8):
    return lib._headtail(self, int(k), True)


def _ml_tail(self, lib, k=8):
    return lib._headtail(self, int(k), False)


ColumnTable.ml_sortrows = _ml_sortrows
ColumnTable.ml_unique = _ml_unique
ColumnTable.ml_isequal = _ml_isequal
ColumnTable.ml_join = _ml_join
ColumnTable.ml_head = _ml_head
ColumnTable.ml_tail = _ml_tail


def install_dispatch(cls) -> None:
    """Make the older builtins answer for datetimes, durations and tables."""
    for name in DISPATCHED:
        base = getattr(cls, "f_" + name, None)
        if base is None:
            continue

        def make(base, name):
            @functools.wraps(base)
            def wrapper(self, *args, **kw):
                if args and hasattr(type(args[0]), "ml_" + name):
                    method = getattr(args[0], "ml_" + name)
                    if "nargout" not in method.__code__.co_varnames:
                        kw.pop("nargout", None)
                    return method(self, *args[1:], **kw)
                if not getattr(base, "_ml_nargout", False):
                    n = kw.pop("nargout", 1)
                    out = base(self, *args, **kw)
                    return out[0] if n == 1 and type(out) is tuple else out
                return base(self, *args, **kw)
            wrapper._ml_nargout = True
            return wrapper
        setattr(cls, "f_" + name, make(base, name))


# ──────────────────────────────────────────────────────────────
#  fitlm
# ──────────────────────────────────────────────────────────────

class LinearModel:
    """What ``fitlm`` returns: a least-squares fit with its statistics."""

    ml_class = "LinearModel"

    def __init__(self, X, y, names, resp, formula) -> None:
        from scipy import stats
        n, p = X.shape
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        fit = X @ beta
        res = y - fit
        dfe = n - p
        sse = float(res @ res)
        mse = sse / dfe if dfe > 0 else np.nan
        cov = mse * np.linalg.pinv(X.T @ X)
        se = np.sqrt(np.diag(cov))
        with np.errstate(divide="ignore", invalid="ignore"):
            tstat = beta / se
        pval = 2 * stats.t.sf(np.abs(tstat), dfe) if dfe > 0 else \
            np.full(p, np.nan)
        has_c = names[0] == "(Intercept)"
        sst = float(((y - y.mean()) ** 2).sum()) if has_c else float(y @ y)
        r2 = 1 - sse / sst if sst else np.nan
        dfm = p - (1 if has_c else 0)
        self._names, self._resp, self._X = names, resp, X
        self.formula = formula
        self.Coefficients = ColumnTable(
            ["Estimate", "SE", "tStat", "pValue"],
            [beta, se, tstat, pval], row_names=list(names))
        self.NumObservations = float(n)
        self.NumCoefficients = float(p)
        self.NumEstimatedCoefficients = float(p)
        self.DFE = float(dfe)
        self.SSE = sse
        self.SST = sst
        self.SSR = sst - sse
        self.MSE = mse
        self.RMSE = float(np.sqrt(mse))
        self.Rsquared = Struct(
            Ordinary=r2, Adjusted=1 - (1 - r2) * (n - (1 if has_c else 0))
            / dfe if dfe > 0 else np.nan)
        self.Fitted = _normalise(fit.reshape(-1, 1))
        self.Residuals = ColumnTable(["Raw"], [res])
        self.CoefficientNames = Cell(names, rows=1)
        self.ResponseName = resp
        self._F = ((self.SSR / dfm) / mse) if dfm > 0 and dfe > 0 else np.nan
        self._p = float(stats.f.sf(self._F, dfm, dfe)) if dfm > 0 and \
            dfe > 0 else np.nan
        self._beta = beta

    def predict(self, Xnew):
        if isinstance(Xnew, ColumnTable):
            cols = [Xnew._data[Xnew.column_index(nm)] for nm in
                    self._pred_names()]
            A = np.column_stack(cols).astype(float)
        else:
            A = _as2d(_as_array(Xnew)).astype(float)
            if A.shape[0] == 1 and A.shape[1] != len(self._pred_names()):
                A = A.T
        if self._names[0] == "(Intercept)":
            A = np.column_stack([np.ones(A.shape[0]), A])
        return _normalise((A @ self._beta).reshape(-1, 1))

    def _pred_names(self):
        return [n for n in self._names if n != "(Intercept)"]

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        if name == "Formula":
            return self.formula
        raise AttributeError(f"Unrecognized property '{name}' for class "
                             f"'LinearModel'.")

    def __repr__(self) -> str:
        r = self.Rsquared
        lines = ["Linear regression model:",
                 f"    {self.formula}", "", "Estimated Coefficients:",
                 repr(self.Coefficients), "",
                 f"Number of observations: {int(self.NumObservations)}, "
                 f"Error degrees of freedom: {int(self.DFE)}",
                 f"Root Mean Squared Error: {self.RMSE:.4g}",
                 f"R-squared: {r['Ordinary']:.4g},  Adjusted R-Squared: "
                 f"{r['Adjusted']:.4g}"]
        if not np.isnan(self._F):
            lines.append(f"F-statistic vs. constant model: {self._F:.4g}, "
                         f"p-value = {self._p:.4g}")
        return "\n".join(lines)


def _fit(X, y, args) -> LinearModel:
    if isinstance(X, ColumnTable):
        formula = y if isinstance(y, str) else None
        if formula is None:
            names = X.columns
            resp = names[-1]
            preds = names[:-1]
            formula = f"{resp} ~ 1 + " + " + ".join(preds)
        else:
            lhs, rhs = (s.strip() for s in formula.split("~", 1))
            resp = lhs
            terms = [t.strip() for t in rhs.replace("-", "+-").split("+")]
            preds = [t for t in terms if t not in ("1", "")]
            if any(t.startswith("-") or ":" in t or "*" in t or "^" in t
                   for t in preds):
                raise MatlabError("fitlm: Evans supports linear terms only "
                                  "in a formula, such as 'y ~ x1 + x2'.")
            if "-1" in terms or "-1" in [t.replace(" ", "") for t in terms]:
                intercept = False
            else:
                intercept = True
            formula = f"{resp} ~ " + ("1 + " if intercept else "") + \
                " + ".join(preds)
            if not intercept:
                return _fit_cols(
                    np.column_stack([X._data[X.column_index(p)]
                                     for p in preds]).astype(float),
                    X._data[X.column_index(resp)].astype(float),
                    list(preds), resp, formula, False)
        cols = np.column_stack([X._data[X.column_index(p)]
                                for p in preds]).astype(float)
        return _fit_cols(cols, X._data[X.column_index(resp)].astype(float),
                         list(preds), resp, formula, True)
    A = _as2d(_as_array(X)).astype(float)
    yy = _as_array(y).astype(float).reshape(-1)
    if A.shape[0] != yy.size and A.shape[1] == yy.size:
        A = A.T
    names = [f"x{i + 1}" for i in range(A.shape[1])]
    return _fit_cols(A, yy, names, "y",
                     "y ~ 1 + " + " + ".join(names), True)


def _fit_cols(A, y, names, resp, formula, intercept) -> LinearModel:
    if intercept:
        A = np.column_stack([np.ones(len(y)), A])
        names = ["(Intercept)"] + names
    return LinearModel(A, y, names, resp, formula)
