"""
Sparse matrices and the iterative solvers.
==========================================
``sparse``, ``speye``, ``spalloc``, ``spdiags``, ``nnz``, ``full``, ``pcg``,
``gmres``, ``bicgstab``, ``eigs`` and the rest, on :mod:`scipy.sparse`.

A sparse matrix is a :class:`Sparse`, a thin box around a ``csc_matrix``. It
is a value of its own so that the operators can tell it from a full matrix:

* ``+ - .* * \\ / '`` and indexing, assignment and ``[A B; C D]`` keep it
  sparse where MATLAB does (``sparse * full`` and ``sparse + scalar`` give a
  full result, as in MATLAB). They are wrapped onto :class:`.Runtime` by
  :func:`install`, so the dense paths pay one ``isinstance`` and nothing else.
* ``size``, ``abs``, ``sum``, ``find``, ``diag`` and the like are rewritten
  here to work on the sparse form.
* Any other library function is handed ``full(A)``: correct, but it
  materialises the matrix, so ``sqrt(A)`` on a huge matrix is not cheap.

Differences from MATLAB: ``A(i, j)`` on one element returns a plain number
(MATLAB returns a 1×1 sparse), and writing into a sparse matrix goes through
``scipy``'s list-of-lists form, so a loop of ``A(i, j) = v`` is quadratic.
"""

from __future__ import annotations

import functools

import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

from . import matlab_runtime as _mr
from .matlab_runtime import (
    COLON,
    Deferred,
    MatlabError,
    Runtime,
    _as2d,
    _as_text,
    _nargout,
    _normalise,
    _number,
)

#: Set once a sparse matrix exists, so dense code never looks for one.
_seen = [False]


class Sparse:
    """A sparse matrix: a ``csc_matrix`` that the operators recognise."""

    __slots__ = ("m",)
    _ml_sparse = True

    def __init__(self, m) -> None:
        self.m = sp.csc_matrix(m)
        self.m.sum_duplicates()
        self.m.eliminate_zeros()           # MATLAB never stores a zero
        _seen[0] = True

    @property
    def shape(self) -> tuple[int, int]:
        return self.m.shape

    def __array__(self, dtype=None, copy=None):
        out = self.m.toarray()
        return out if dtype is None else out.astype(dtype)

    def __len__(self) -> int:
        return max(self.m.shape)

    def __repr__(self) -> str:
        return sparse_text(self)


# ── conversions ───────────────────────────────────────────────────

def is_sparse(x) -> bool:
    return isinstance(x, Sparse)


def dense(x):
    """``full(x)`` in the runtime's own form (1×1 → number, 1×n → row)."""
    if isinstance(x, Sparse):
        return _normalise(x.m.toarray())
    return x


def _csc(x, who: str = "this operation"):
    """Any numeric value as a ``csc_matrix``."""
    if isinstance(x, Sparse):
        return x.m
    if isinstance(x, (bool, int, float, complex, np.number, np.bool_)):
        return sp.csc_matrix(np.array([[x]]))
    if isinstance(x, np.ndarray):
        return sp.csc_matrix(_as2d(x))
    if x is None:
        return sp.csc_matrix((0, 0))
    raise MatlabError(f"{who}: a sparse matrix cannot be combined with "
                      f"this kind of value.")


def _proxy(x: Sparse) -> np.ndarray:
    """A read-only array of the same shape and type that costs no memory."""
    return np.broadcast_to(np.zeros((), dtype=x.m.dtype), x.shape)


def _is_scalar(x) -> bool:
    return isinstance(x, (bool, int, float, complex, np.number, np.bool_)) \
        or (isinstance(x, np.ndarray) and x.size == 1)


def _scalar(x):
    return x.reshape(-1)[0].item() if isinstance(x, np.ndarray) else x


def _int(x, what: str) -> int:
    v = float(_scalar(x))
    if v != int(v) or v < 0:
        raise MatlabError(f"{what} must be a nonnegative integer.")
    return int(v)


# ── display ───────────────────────────────────────────────────────

#: Entries shown before the listing is cut; a million is no help in a console.
_SHOWN = 200


def sparse_text(x: Sparse) -> str:
    """The ``(row,col)   value`` listing MATLAB prints for a sparse matrix."""
    m = x.m.tocoo()
    r, c = m.shape
    if m.nnz == 0:
        return f"   All zero sparse: {r}-by-{c}"
    order = np.lexsort((m.row, m.col))
    row, col, val = m.row[order], m.col[order], m.data[order]
    count = len(val)
    keep = min(count, _SHOWN)
    pos = [f"({row[k] + 1},{col[k] + 1})" for k in range(keep)]
    txt = [_number(val[k].item()) for k in range(keep)]
    pw, vw = max(map(len, pos)), max(map(len, txt))
    lines = [f"   {p.ljust(pw)}    {t.rjust(vw)}" for p, t in zip(pos, txt)]
    if count > keep:
        lines.append(f"   ... {count - keep} more of {count} nonzeros")
    return "\n".join(lines)


# ── operators ─────────────────────────────────────────────────────

def _same_size(a: sp.spmatrix, b: sp.spmatrix) -> None:
    if a.shape != b.shape:
        raise MatlabError(
            f"Arrays have incompatible sizes for this operation: "
            f"{a.shape[0]}×{a.shape[1]} and {b.shape[0]}×{b.shape[1]}.")


def _plus(rt, a, b, orig, sign=1):
    if isinstance(a, Sparse) and isinstance(b, Sparse):
        _same_size(a.m, b.m)
        return Sparse(a.m + sign * b.m)
    return orig(rt, dense(a), dense(b))


def _times(rt, a, b, orig):
    """``.*``: sparse with a scalar or with an equal-size array stays sparse."""
    if _is_scalar(a) and isinstance(b, Sparse):
        return Sparse(b.m * _scalar(a))
    if _is_scalar(b) and isinstance(a, Sparse):
        return Sparse(a.m * _scalar(b))
    if isinstance(a, Sparse) and isinstance(b, (Sparse, np.ndarray)):
        other = _csc(b)
        if other.shape == a.shape:
            return Sparse(a.m.multiply(other))
    if isinstance(b, Sparse) and isinstance(a, np.ndarray):
        other = _csc(a)
        if other.shape == b.shape:
            return Sparse(b.m.multiply(other))
    return orig(rt, dense(a), dense(b))


def _rdivide(rt, a, b, orig):
    if isinstance(a, Sparse) and _is_scalar(b) and _scalar(b) != 0:
        return Sparse(a.m / _scalar(b))
    return orig(rt, dense(a), dense(b))


def _power(rt, a, b, orig):
    if isinstance(a, Sparse) and _is_scalar(b) and np.isrealobj(
            _scalar(b)) and float(_scalar(b)) > 0:
        return Sparse(a.m.power(_scalar(b)))
    return orig(rt, dense(a), dense(b))


def _mtimes(rt, a, b, orig):
    if _is_scalar(a) and not isinstance(a, Sparse):
        return Sparse(b.m * _scalar(a)) if isinstance(b, Sparse) \
            else orig(rt, a, dense(b))
    if _is_scalar(b) and not isinstance(b, Sparse):
        return Sparse(a.m * _scalar(b)) if isinstance(a, Sparse) \
            else orig(rt, dense(a), b)
    left, right = _csc(a), _csc(b)
    if left.shape[1] != right.shape[0]:
        raise MatlabError(
            f"Incorrect dimensions for matrix multiplication: "
            f"{left.shape[0]}×{left.shape[1]} * "
            f"{right.shape[0]}×{right.shape[1]}. "
            f"Use .* for elementwise multiplication.")
    if isinstance(a, Sparse) and isinstance(b, Sparse):
        return Sparse(left @ right)
    if isinstance(a, Sparse):                    # sparse * full → full
        return _normalise(np.asarray(left @ _as2d(b)))
    return _normalise(np.asarray((right.T @ _as2d(a).T).T))


def _solve(A: sp.csc_matrix, B):
    """``A \\ B`` for a sparse ``A``; ``B`` full or sparse."""
    n, m = A.shape
    if n == m:
        try:
            lu = spla.splu(A.tocsc())
        except RuntimeError:
            raise MatlabError("Matrix is singular to working precision."
                              ) from None
        rhs = B.toarray() if sp.issparse(B) else _as2d(B)
        if rhs.shape[0] == 1 and n > 1:
            rhs = rhs.T
        if rhs.shape[0] != n:
            raise MatlabError(
                f"Arrays have incompatible sizes for this operation: "
                f"{n}×{m} and {rhs.shape[0]}×{rhs.shape[1]}.")
        out = lu.solve(rhs.astype(complex if np.iscomplexobj(rhs)
                                  or np.iscomplexobj(A.data) else float))
        return out
    rhs = B.toarray() if sp.issparse(B) else _as2d(B)
    return np.linalg.lstsq(A.toarray(), rhs, rcond=None)[0]


def _mldivide(rt, a, b, orig):
    if isinstance(a, Sparse):
        if b is None:
            return orig(rt, dense(a), dense(b))
        if a.shape == (1, 1):
            return rt.rdivide(b, a.m[0, 0]) if not isinstance(b, Sparse) \
                else Sparse(b.m / a.m[0, 0])
        out = _solve(a.m, b.m if isinstance(b, Sparse) else b)
        return Sparse(out) if isinstance(b, Sparse) else _normalise(out)
    return orig(rt, a, dense(b))


def _mrdivide(rt, a, b, orig):
    if isinstance(b, Sparse) and b.shape != (1, 1):
        left = _csc(a)
        out = _solve(b.m.T.tocsc(), left.T.tocsc()
                     if isinstance(a, Sparse) else left.T.toarray()).T
        return Sparse(out) if isinstance(a, Sparse) else _normalise(out)
    if isinstance(a, Sparse) and _is_scalar(b) or (
            isinstance(b, Sparse) and b.shape == (1, 1)):
        s = b.m[0, 0] if isinstance(b, Sparse) else _scalar(b)
        return Sparse(a.m / s) if isinstance(a, Sparse) else a / s
    return orig(rt, dense(a), dense(b))


def _mpower(rt, a, b, orig):
    if isinstance(a, Sparse) and _is_scalar(b):
        p = float(_scalar(b))
        if p == int(p) and p >= 0 and a.shape[0] == a.shape[1]:
            return Sparse(spla.matrix_power(a.m, int(p)))
    return orig(rt, dense(a), dense(b))


def _compare(op):
    def handler(rt, a, b, orig):
        for x, y, flip in ((a, b, False), (b, a, True)):
            if isinstance(x, Sparse) and _is_scalar(y):
                s = _scalar(y)
                zero = op(0, s) if not flip else op(s, 0)
                if not zero:             # zeros stay false: stays sparse
                    d = x.m.tocoo()
                    keep = op(d.data, s) if not flip else op(s, d.data)
                    return Sparse(sp.coo_matrix(
                        (keep.astype(bool), (d.row, d.col)), shape=x.shape))
        return orig(rt, dense(a), dense(b))
    return handler


# ── indexing and assignment ───────────────────────────────────────

def _linear(rt, x: Sparse, arg):
    r, c = x.shape
    if arg is COLON:
        return Sparse(x.m.tocoo().reshape((r * c, 1), order="F"))
    if isinstance(arg, Sparse):
        arg = dense(arg)
    idx = rt._indices(arg, r * c)
    scalar = np.ndim(idx) == 0
    ids = np.atleast_1d(idx)
    vals = np.asarray(x.m[ids % r, ids // r]).reshape(-1)
    if scalar:
        return vals[0].item()
    shape = np.shape(arg)
    if len(shape) == 2 and min(shape) > 1 and np.asarray(arg).dtype != bool:
        out = vals.reshape(shape)
    elif c == 1 and r > 1:                      # a column stays a column
        out = vals.reshape(-1, 1)
    elif r == 1:
        out = vals.reshape(1, -1)
    elif len(shape) == 2 and shape[1] == 1:     # A(column index) of a matrix
        out = vals.reshape(-1, 1)
    else:
        out = vals.reshape(1, -1)
    return Sparse(sp.csc_matrix(out))


def _index(rt, x: Sparse, args: tuple):
    if not args:
        return x
    r, c = x.shape
    if len(args) == 1:
        return _linear(rt, x, args[0])
    extra = args[2:]
    if any(_mr._resolve(e, 1) not in (1, COLON) for e in extra):
        raise MatlabError("Index exceeds the array dimensions.")
    rows = np.atleast_1d(rt._indices(args[0], r))
    cols = np.atleast_1d(rt._indices(args[1], c))
    out = x.m.tocsr()[rows][:, cols]
    if out.shape == (1, 1):
        return out[0, 0].item()
    return Sparse(out)


def _assign(rt, x: Sparse, path: list, value):
    (kind, key), rest = path[0], path[1:]
    if kind != "()" or rest:
        raise MatlabError("Only A(i, j) = value can write into a sparse "
                          "matrix.")
    args = tuple(key) if isinstance(key, (tuple, list)) else (key,)
    r, c = x.shape
    if isinstance(value, Sparse):
        value = dense(value)
    empty = value is None or (isinstance(value, np.ndarray)
                              and value.size == 0)
    m = x.m.tolil()
    if len(args) == 1:
        idx = args[0]
        ids = np.arange(r * c) if idx is COLON else np.atleast_1d(
            rt._indices(_dense_arg(idx), max(r * c, _top(idx) or 0)))
        if empty:
            raise MatlabError("A null assignment can have only one "
                              "non-colon index.")
        vals = _fit(value, len(ids), r, c)
        if ids.size and ids.max() >= r * c:
            raise MatlabError("Attempt to grow a sparse matrix by linear "
                              "index; use A(i, j).")
        for k, i in enumerate(ids):
            m[i % r, i // r] = vals[k]
        return Sparse(m.tocsc())
    if len(args) > 2 and any(_mr._resolve(e, 1) not in (1, COLON)
                             for e in args[2:]):
        raise MatlabError("Index exceeds the array dimensions.")
    a0, a1 = args[0], args[1]
    if empty:                                    # A(i, :) = []
        if a0 is COLON and a1 is not COLON:
            drop = set(np.atleast_1d(rt._indices(_dense_arg(a1), c)))
            keep = [j for j in range(c) if j not in drop]
            return Sparse(x.m.tocsc()[:, keep])
        if a1 is COLON and a0 is not COLON:
            drop = set(np.atleast_1d(rt._indices(_dense_arg(a0), r)))
            keep = [i for i in range(r) if i not in drop]
            return Sparse(x.m.tocsr()[keep, :])
        raise MatlabError("A null assignment can have only one non-colon "
                          "index.")
    rows = np.arange(r) if a0 is COLON else np.atleast_1d(
        _grow(rt, a0, r))
    cols = np.arange(c) if a1 is COLON else np.atleast_1d(
        _grow(rt, a1, c))
    nr, nc = max(r, int(rows.max()) + 1 if rows.size else 0), \
        max(c, int(cols.max()) + 1 if cols.size else 0)
    if (nr, nc) != (r, c):
        m.resize((nr, nc))
    vals = _fit(value, rows.size * cols.size, rows.size, cols.size)
    block = np.asarray(vals).reshape(rows.size, cols.size, order="F") \
        if np.ndim(vals) else vals
    m[np.ix_(rows, cols)] = block
    return Sparse(m.tocsc())


def _dense_arg(arg):
    return dense(arg) if isinstance(arg, Sparse) else arg


def _top(arg):
    a = np.asarray(_dense_arg(arg))
    return int(a.max()) if a.size and a.dtype != bool else None


def _grow(rt, arg, n: int):
    """0-based indices that may point past the end (the matrix then grows)."""
    arg = _dense_arg(arg)
    a = np.asarray(_mr._resolve(arg, n))
    if a.dtype == bool:
        return rt._indices(arg, n)
    if a.size and (np.any(a < 1) or np.any(a != np.round(a))):
        raise MatlabError("Array indices must be positive integers.")
    return (a.astype(int) - 1).reshape(-1)


def _fit(value, count: int, rows: int, cols: int):
    """The value to write, as ``count`` numbers (a scalar repeats)."""
    v = np.asarray(value)
    if v.size == 1:
        return np.full(count, v.reshape(-1)[0])
    if v.size != count:
        raise MatlabError(
            f"Unable to perform assignment because the size of the left "
            f"side is {rows}-by-{cols} and the size of the right side is "
            f"{_as2d(v).shape[0]}-by-{_as2d(v).shape[1]}.")
    return v.reshape(-1, order="F")


def _concat(rt, rows: list[list], orig):
    flat = [x for row in rows for x in row]
    if any(isinstance(x, Deferred) for x in flat):
        return orig(rt, rows)
    lines = []
    for row in rows:
        parts = [_csc(x) for x in row
                 if not (x is None or (isinstance(x, np.ndarray)
                                       and x.size == 0))]
        if parts:
            try:
                lines.append(sp.hstack(parts, format="csc"))
            except ValueError:
                raise MatlabError("Dimensions of arrays being concatenated "
                                  "are not consistent.") from None
    if not lines:
        return Sparse(sp.csc_matrix((0, 0)))
    try:
        return Sparse(sp.vstack(lines, format="csc"))
    except ValueError:
        raise MatlabError("Dimensions of arrays being concatenated are "
                          "not consistent.") from None


# ── library functions that know about sparse ──────────────────────

def _ok(fn):
    """Mark a library function as taking a :class:`Sparse` as it is."""
    fn._ml_sparse_ok = True
    return fn


def _overload(name: str, sparse_impl, *, outputs: bool = False):
    """``f_<name>`` tries ``sparse_impl`` when its first argument is sparse."""
    orig = getattr(_mr._Library, f"f_{name}")

    @functools.wraps(orig)
    def method(self, *args, **kwargs):
        if args and isinstance(args[0], Sparse):
            return sparse_impl(self, *args, **kwargs)
        # a full call, but another argument may be sparse (e.g. isequal)
        return orig(self, *(dense(a) for a in args), **kwargs)
    if outputs:
        _nargout(method)
    setattr(_mr._Library, f"f_{name}", _ok(method))
    return orig


def _metadata(name: str):
    """Functions that only need the shape and type of a sparse matrix."""
    orig = getattr(_mr._Library, f"f_{name}", None)
    if orig is None:
        return

    @functools.wraps(orig)
    def method(self, *args, **kwargs):
        if args and isinstance(args[0], Sparse):
            args = (_proxy(args[0]),) + args[1:]
        return orig(self, *args, **kwargs)
    setattr(_mr._Library, f"f_{name}", _ok(method))


_METADATA = ("size", "numel", "length", "isempty", "ndims", "isscalar",
             "isvector", "isrow", "iscolumn", "ismatrix", "issquare",
             "columns", "rows", "class", "isnumeric", "isreal", "isfloat",
             "islogical", "isa")


def _axis(x: Sparse, dim) -> int:
    if dim is None:
        return 1 if x.shape[0] == 1 else 0
    d = int(_scalar(dim))
    if d not in (1, 2):
        raise MatlabError("The dimension must be 1 or 2.")
    return d - 1


def _s_sum(self, x, dim=None, *_):
    ax = _axis(x, dim)
    return Sparse(sp.csc_matrix(x.m.sum(axis=ax)))


def _s_abs(self, x):
    return Sparse(abs(x.m))


def _s_diag(self, x, k=0):
    k = int(_scalar(k))
    r, c = x.shape
    if r == 1 or c == 1:                           # a vector → a matrix
        v = x.m.toarray().reshape(-1)
        n = v.size + abs(k)
        return Sparse(sp.diags(v, k, shape=(n, n)))
    return Sparse(sp.csc_matrix(x.m.diagonal(k).reshape(-1, 1)))


def _s_find(self, x, n=None, direction="first", nargout=1):
    m = x.m.tocoo()
    order = np.lexsort((m.row, m.col))
    row, col, val = m.row[order], m.col[order], m.data[order]
    keep = val != 0
    row, col, val = row[keep], col[keep], val[keep]
    if n is not None:
        k = int(_scalar(n))
        sel = slice(-k, None) if str(direction).lower() == "last" \
            else slice(0, k)
        row, col, val = row[sel], col[sel], val[sel]
    r = x.shape[0]
    if nargout <= 1:
        out = (row + col * r + 1).astype(float)
        return out.reshape(1, -1) if x.shape[0] == 1 and out.size else \
            _col(out)
    result = [_col(row + 1.0), _col(col + 1.0), _col(val.astype(
        float if not np.iscomplexobj(val) else complex))]
    return tuple(result[:nargout])


def _col(v: np.ndarray):
    v = np.asarray(v).reshape(-1, 1)
    return _normalise(v)


def _s_trace(self, x):
    return x.m.diagonal().sum().item()


def _s_norm(self, x, p=2):
    if isinstance(p, str):
        p = p.lower()
        if p in ("fro", "f"):
            return float(spla.norm(x.m, "fro"))
        if p == "inf":
            return float(spla.norm(x.m, np.inf))
        raise MatlabError(f"Unknown norm type '{p}'.")
    p = float(_scalar(p))
    if p == 1:
        return float(spla.norm(x.m, 1))
    if np.isinf(p):
        return float(spla.norm(x.m, np.inf))
    if p == 2:
        return float(np.linalg.norm(x.m.toarray(), 2))
    raise MatlabError("Only the 1, 2, Inf and 'fro' norms of a sparse "
                      "matrix are defined.")


def _s_kron(self, a, b):
    return Sparse(sp.kron(_csc(a), _csc(b), format="csc"))


def _s_tril(self, x, k=0):
    return Sparse(sp.tril(x.m, int(_scalar(k)), format="csc"))


def _s_triu(self, x, k=0):
    return Sparse(sp.triu(x.m, int(_scalar(k)), format="csc"))


def _s_disp(self, x):
    print(sparse_text(x))


def _sparse_aware_binary(name: str, handler):
    orig = getattr(Runtime, name)

    @functools.wraps(orig)
    def op(self, a, b):
        if isinstance(a, Sparse) or isinstance(b, Sparse):
            return handler(self, a, b, orig)
        return orig(self, a, b)
    setattr(Runtime, name, op)


# ── the MATLAB functions ──────────────────────────────────────────

class SparseLibrary:
    """Constructors, queries and solvers."""

    # sparse(A) / sparse(m, n) / sparse(i, j, v[, m, n[, nzmax]])
    def f_sparse(self, *args):
        n = len(args)
        if n == 1:
            a = args[0]
            if isinstance(a, Sparse):
                return a
            return Sparse(_csc(a, "sparse"))
        if n == 2:
            return Sparse(sp.csc_matrix((_int(args[0], "sparse: m"),
                                         _int(args[1], "sparse: n"))))
        if n not in (3, 5, 6):
            raise MatlabError("sparse expects 1, 2, 3, 5 or 6 arguments.")
        i, j, v = (np.asarray(dense(a)).reshape(-1) for a in args[:3])
        if i.dtype == bool or j.dtype == bool:
            raise MatlabError("Subscripts must be positive integers.")
        size = max(i.size, j.size, v.size)
        for a in (i, j, v):
            if a.size not in (1, size):
                raise MatlabError("Vectors must be the same length.")
        i, j, v = (np.broadcast_to(a, (size,)) for a in (i, j, v))
        if size and (np.any(i < 1) or np.any(j < 1)
                     or np.any(i != np.round(i)) or np.any(j != np.round(j))):
            raise MatlabError("Subscripts must be positive integers.")
        i, j = i.astype(int) - 1, j.astype(int) - 1
        m = _int(args[3], "sparse: m") if n >= 5 else (
            int(i.max()) + 1 if size else 0)
        k = _int(args[4], "sparse: n") if n >= 5 else (
            int(j.max()) + 1 if size else 0)
        if size and (i.max() >= m or j.max() >= k):
            raise MatlabError("Index exceeds matrix dimensions.")
        # coo → csc adds duplicates, as MATLAB does
        return Sparse(sp.coo_matrix((v, (i, j)), shape=(m, k)))

    def f_speye(self, *dims):
        if len(dims) == 1 and isinstance(dims[0], np.ndarray):
            dims = tuple(dims[0].reshape(-1))
        if len(dims) == 1:
            dims = (dims[0], dims[0])
        if len(dims) != 2:
            raise MatlabError("speye expects speye(n), speye(m, n) or "
                              "speye([m n]).")
        return Sparse(sp.eye(_int(dims[0], "speye: m"),
                             _int(dims[1], "speye: n"), format="csc"))

    def f_spalloc(self, m, n, nz=0):
        return Sparse(sp.csc_matrix((_int(m, "spalloc: m"),
                                     _int(n, "spalloc: n"))))

    def f_spones(self, a):
        m = _csc(a, "spones").tocoo()
        return Sparse(sp.coo_matrix((np.ones(m.nnz), (m.row, m.col)),
                                    shape=m.shape))

    def f_sprand(self, *args):
        if len(args) == 1:
            m = _csc(args[0], "sprand").tocoo()
            vals = np.random.rand(m.nnz)
            return Sparse(sp.coo_matrix((vals, (m.row, m.col)),
                                        shape=m.shape))
        if len(args) != 3:
            raise MatlabError("sprand expects sprand(S) or "
                              "sprand(m, n, density).")
        m, n = _int(args[0], "sprand: m"), _int(args[1], "sprand: n")
        density = float(_scalar(args[2]))
        if not 0 <= density <= 1:
            raise MatlabError("The density must be between 0 and 1.")
        count = int(round(density * m * n))
        flat = np.random.choice(m * n, size=count, replace=False) \
            if count else np.zeros(0, int)
        return Sparse(sp.coo_matrix((np.random.rand(count),
                                     (flat % m, flat // m)), shape=(m, n)))

    def f_full(self, a):
        return dense(a)

    def f_issparse(self, a):
        return isinstance(a, Sparse)

    def f_nnz(self, a):
        if isinstance(a, Sparse):
            m = a.m.copy()
            m.eliminate_zeros()
            return m.nnz
        return int(np.count_nonzero(dense(a) if a is not None else 0))

    def f_nzmax(self, a):
        return a.m.nnz if isinstance(a, Sparse) else \
            int(np.size(dense(a)))

    def f_nonzeros(self, a):
        if isinstance(a, Sparse):
            m = a.m.tocoo()
            order = np.lexsort((m.row, m.col))
            vals = m.data[order]
            vals = vals[vals != 0]
        else:
            arr = np.asarray(dense(a) if a is not None else []).reshape(
                -1, order="F")
            vals = arr[arr != 0]
        return _col(vals.astype(complex if np.iscomplexobj(vals) else float))

    def f_spfun(self, fn, a):
        m = _csc(a, "spfun").tocoo()
        data = np.asarray(self.rt.call(fn, (m.data,), nargout=1)).reshape(-1)
        return Sparse(sp.coo_matrix((data, (m.row, m.col)), shape=m.shape))

    @_nargout
    def f_spdiags(self, *args, nargout=1):
        """Build, extract or replace diagonals; see the help page."""
        if len(args) == 1:
            B, d = self._spdiags_extract(args[0], None)
            return (B, d)[:max(nargout, 1)] if nargout > 1 else B
        if len(args) == 2:
            return self._spdiags_extract(args[0], args[1])[0]
        if len(args) == 3:                       # spdiags(B, d, A): replace
            B, d, A = args
            return self._spdiags_replace(B, d, A)
        if len(args) != 4:
            raise MatlabError("spdiags expects spdiags(A), spdiags(A, d), "
                              "spdiags(B, d, A) or spdiags(B, d, m, n).")
        B, d, m, n = args
        return self._spdiags_build(B, d, _int(m, "spdiags: m"),
                                   _int(n, "spdiags: n"))

    def _spdiags_build(self, B, d, m, n):
        diags = _diag_numbers(d)
        data = _as2d(np.asarray(dense(B)))
        if data.shape[1] != len(diags):
            raise MatlabError("The number of columns of B must equal the "
                              "number of diagonals.")
        if m >= n:                      # column-aligned, as MATLAB
            return Sparse(sp.dia_matrix((_pad(data.T, n), diags),
                                        shape=(m, n)))
        # m < n: entries line up with the row, so build the transpose
        return Sparse(sp.dia_matrix((_pad(data.T, m), [-k for k in diags]),
                                    shape=(n, m)).T)

    def _spdiags_extract(self, A, d):
        m = _csc(A, "spdiags")
        r, c = m.shape
        if d is None:
            coo = m.tocoo()
            diags = sorted(set((coo.col - coo.row)[coo.data != 0].tolist()))
        else:
            diags = _diag_numbers(d)
        length = min(r, c)
        out = np.zeros((length if r >= c else r, len(diags)), m.dtype)
        coo = m.tocoo()
        for k, off in enumerate(diags):
            sel = (coo.col - coo.row) == off
            pos = coo.col[sel] if r >= c else coo.row[sel]
            out[pos, k] = coo.data[sel]
        return _normalise(out), _col(np.array(diags, float))

    def _spdiags_replace(self, B, d, A):
        m = _csc(A, "spdiags").tolil()
        r, c = m.shape
        diags = _diag_numbers(d)
        data = _as2d(np.asarray(dense(B)))
        for k, off in enumerate(diags):
            for i in range(max(0, -off), min(r, c - off)):
                j = i + off
                pos = j if r >= c else i
                m[i, j] = data[pos, k] if pos < data.shape[0] else 0
        return Sparse(m.tocsc())

    # ── iterative solvers ───────────────────────────────────────

    def _krylov(self, name, scipy_fn, A, b, tol, maxit, M1, M2, x0, nargout,
                restart=None):
        op, n = _operator(self.rt, A, name)
        rhs = np.asarray(dense(b), dtype=complex if np.iscomplexobj(
            dense(b)) else float).reshape(-1)
        if rhs.size != n:
            raise MatlabError(f"The right hand side vector must have {n} "
                              f"rows.")
        tol = 1e-6 if tol is None or _empty(tol) else float(_scalar(tol))
        maxit = min(n, 20) if maxit is None or _empty(maxit) \
            else int(_scalar(maxit))
        guess = None if x0 is None or _empty(x0) else \
            np.asarray(dense(x0), float).reshape(-1)
        precond = _preconditioner(self.rt, M1, M2, n)
        norm_b = np.linalg.norm(rhs)
        if norm_b == 0:
            out = np.zeros(n)
            return self._krylov_result(name, out, 0, 0.0, 0, [0.0], nargout)
        history: list[float] = []

        def residual(x) -> float:
            return float(np.linalg.norm(rhs - op.matvec(x)))

        def callback(arg):
            # scipy hands cg/bicgstab the iterate and gmres the residual norm
            history.append(float(arg) * norm_b if name == "gmres"
                            and np.ndim(arg) == 0 else residual(arg))
        kwargs = dict(rtol=tol, maxiter=maxit, M=precond, x0=guess,
                      callback=callback)
        if name == "gmres":
            kwargs.update(restart=restart or n, callback_type="pr_norm")
            kwargs["maxiter"] = maxit
        if name == "minres":
            kwargs.pop("maxiter")
            kwargs["maxiter"] = maxit
        try:
            x, info = scipy_fn(op, rhs, **kwargs)
        except TypeError:
            kwargs["tol"] = kwargs.pop("rtol")            # older SciPy
            x, info = scipy_fn(op, rhs, **kwargs)
        relres = residual(x) / norm_b
        iters = len(history)
        if name == "gmres":                  # [outer inner], as MATLAB
            size = restart or n
            outer = max((iters - 1) // size + 1, 1)
            iters = np.array([outer, iters - (outer - 1) * size], float)
        flag = 0 if info == 0 or relres <= tol else (
            1 if info > 0 else 3)
        return self._krylov_result(name, x, flag, relres, iters,
                                   [norm_b] + history, nargout)

    def _krylov_result(self, name, x, flag, relres, iters, resvec, nargout):
        x = _normalise(np.asarray(x).reshape(-1, 1))
        pair = isinstance(iters, np.ndarray)
        where = (f"outer iteration {int(iters[0])} (inner iteration "
                 f"{int(iters[1])})" if pair else f"iteration {iters}")
        if nargout < 2:
            if flag == 0:
                print(f"{name} converged at {where} to a solution "
                      f"with relative residual {relres:.2g}.")
            else:
                print(f"{name} stopped at {where} without "
                      f"converging to the desired tolerance; the relative "
                      f"residual is {relres:.2g}.")
        outs = [x, float(flag), float(relres),
                iters if pair else float(iters),
                _col(np.array(resvec, float))]
        return tuple(outs[:max(nargout, 1)]) if nargout > 1 else outs[0]

    @_nargout
    def f_pcg(self, A, b, tol=None, maxit=None, M1=None, M2=None, x0=None,
              nargout=1):
        return self._krylov("pcg", spla.cg, A, b, tol, maxit, M1, M2, x0,
                            nargout)

    @_nargout
    def f_bicgstab(self, A, b, tol=None, maxit=None, M1=None, M2=None,
                   x0=None, nargout=1):
        return self._krylov("bicgstab", spla.bicgstab, A, b, tol, maxit,
                            M1, M2, x0, nargout)

    @_nargout
    def f_bicg(self, A, b, tol=None, maxit=None, M1=None, M2=None, x0=None,
               nargout=1):
        return self._krylov("bicg", spla.bicg, A, b, tol, maxit, M1, M2, x0,
                            nargout)

    @_nargout
    def f_minres(self, A, b, tol=None, maxit=None, M1=None, M2=None,
                 x0=None, nargout=1):
        return self._krylov("minres", spla.minres, A, b, tol, maxit, M1, M2,
                            x0, nargout)

    @_nargout
    def f_gmres(self, A, b, restart=None, tol=None, maxit=None, M1=None,
                M2=None, x0=None, nargout=1):
        n = _operator(self.rt, A, "gmres")[1]
        restart = None if restart is None or _empty(restart) \
            else int(_scalar(restart))
        if restart is not None and restart >= n:
            restart = None
        maxit = min(n, 10) if maxit is None or _empty(maxit) else maxit
        return self._krylov("gmres", spla.gmres, A, b, tol, maxit, M1, M2,
                            x0, nargout, restart=restart)

    # ── eigenvalues and singular values ─────────────────────────

    @_nargout
    def f_eigs(self, A, *args, nargout=1):
        """``d = eigs(A, k, sigma)`` and ``[V, D] = eigs(A, k, sigma)``."""
        if callable(A) and not isinstance(A, (np.ndarray, Sparse)):
            raise MatlabError("eigs with a function handle is not in Evans; "
                              "pass the matrix.")
        mat = _csc(A, "eigs")
        n = mat.shape[0]
        if mat.shape[0] != mat.shape[1]:
            raise MatlabError("Input matrix must be square.")
        args = list(args)
        B = None
        if args and (isinstance(args[0], Sparse) or (
                isinstance(args[0], np.ndarray) and args[0].ndim == 2
                and args[0].size > 1)):
            B = _csc(args.pop(0))
        k = min(6, n) if not args or _empty(args[0]) \
            else int(_scalar(args[0]))
        sigma = args[1] if len(args) > 1 else "largestabs"
        if len(args) > 2:
            raise MatlabError("eigs options structures are not in Evans.")
        k = max(1, min(k, n))
        which, shift = _eigs_target(sigma)
        symmetric = (mat - mat.T).nnz == 0 and not np.iscomplexobj(mat.data) \
            if n < 20000 else False
        if n <= max(k + 2, 40) or B is not None and n <= 40:
            vals, vecs = _dense_eigs(mat, B, k, which, shift)
        else:
            solver = spla.eigsh if symmetric else spla.eigs
            kw = {"M": B} if B is not None else {}
            if shift is not None:
                kw.update(sigma=shift, which="LM")
            else:
                kw.update(which=which)
            try:
                vals, vecs = solver(mat.astype(float if not np.iscomplexobj(
                    mat.data) else complex), k=k, **kw)
            except spla.ArpackNoConvergence as exc:
                raise MatlabError("eigs: ARPACK did not converge.") \
                    from exc
            vals, vecs = _order(vals, vecs, which, shift)
        if nargout <= 1:
            return _col(_clean(vals))
        D = np.diag(_clean(vals))
        return (_normalise(_clean(vecs)), _normalise(D),
                0.0)[:max(nargout, 1)]

    @_nargout
    def f_svds(self, A, k=6, sigma="largest", nargout=1):
        mat = _csc(A, "svds")
        k = max(1, min(int(_scalar(k)), min(mat.shape) - 1 or 1))
        which = "SM" if str(sigma).lower() in ("smallest", "0") else "LM"
        if min(mat.shape) <= 2 or k >= min(mat.shape):
            u, s, vh = np.linalg.svd(mat.toarray())
            u, s, vh = u[:, :k], s[:k], vh[:k]
        else:
            u, s, vh = spla.svds(mat.astype(float), k=k, which=which)
            order = np.argsort(-s)
            u, s, vh = u[:, order], s[order], vh[order]
        if nargout <= 1:
            return _col(s)
        return (_normalise(u), _normalise(np.diag(s)),
                _normalise(vh.T))[:nargout]


def _diag_numbers(d) -> list[int]:
    return [int(v) for v in np.asarray(dense(d), float).reshape(-1)]


def _pad(data: np.ndarray, length: int) -> np.ndarray:
    """B's columns as rows of length ``length`` (zero-padded or cut)."""
    out = np.zeros((data.shape[0], length), data.dtype)
    take = min(length, data.shape[1])
    out[:, :take] = data[:, :take]
    return out


def _empty(x) -> bool:
    return x is None or (isinstance(x, np.ndarray) and x.size == 0)


def _clean(a: np.ndarray) -> np.ndarray:
    """Drop a numerically zero imaginary part, as eigs does for real input."""
    if np.iscomplexobj(a) and np.all(np.abs(a.imag) <= 1e-12 * max(
            1.0, np.abs(a).max() if a.size else 1.0)):
        return a.real
    return a


def _eigs_target(sigma):
    if isinstance(sigma, str):
        key = sigma.lower()
        table = {"largestabs": "LM", "lm": "LM", "smallestabs": "SM",
                 "sm": "SM", "largestreal": "LR", "lr": "LR", "la": "LA",
                 "smallestreal": "SR", "sr": "SR", "sa": "SA",
                 "bothendsreal": "BE", "be": "BE"}
        if key not in table:
            raise MatlabError(f"Unknown eigs target '{_as_text(sigma)}'.")
        which = table[key]
        return (which, 0.0) if which == "SM" else (which, None)
    return "LM", complex(_scalar(sigma)) if np.iscomplexobj(sigma) \
        else float(_scalar(sigma))


def _order(vals, vecs, which, shift):
    if shift is not None:
        key = np.abs(vals - shift)
    elif which in ("LM",):
        key = -np.abs(vals)
    elif which in ("LR", "LA"):
        key = -vals.real
    elif which in ("SR", "SA"):
        key = vals.real
    else:
        key = -np.abs(vals)
    idx = np.argsort(key, kind="stable")
    return vals[idx], vecs[:, idx]


def _dense_eigs(mat, B, k, which, shift):
    a = mat.toarray()
    if B is not None:
        import scipy.linalg as sl
        vals, vecs = sl.eig(a, B.toarray())
    else:
        vals, vecs = np.linalg.eig(a)
    if shift is None and which == "SM":
        shift = 0.0
    if which == "BE":
        idx = np.argsort(vals.real)
        lo, hi = idx[:k // 2], idx[len(idx) - (k - k // 2):]
        pick = np.concatenate([lo, hi])
        return vals[pick], vecs[:, pick]
    vals, vecs = _order(vals, vecs, which, shift)
    return vals[:k], vecs[:, :k]


def _operator(rt, A, who: str):
    """``A`` (matrix or function handle) as a LinearOperator, and its size."""
    if isinstance(A, (Sparse, np.ndarray)) or _scalar_like(A):
        m = _csc(A, who)
        if m.shape[0] != m.shape[1]:
            raise MatlabError("The coefficient matrix must be square.")
        return spla.aslinearoperator(m), m.shape[0]
    raise MatlabError(f"{who}: a function handle for A is not supported "
                      f"yet; pass the matrix.")


def _scalar_like(x) -> bool:
    return isinstance(x, (int, float, complex, np.number))


def _preconditioner(rt, M1, M2, n: int):
    """MATLAB's ``M = M1*M2`` (applied as ``M \\ x``) as scipy's ``M``."""
    parts = [m for m in (M1, M2) if not _empty(m)]
    if not parts:
        return None
    solvers = []
    for m in parts:
        if isinstance(m, (Sparse, np.ndarray)):
            mat = _csc(m)
            lu = spla.splu(mat)
            solvers.append(lu.solve)
        else:
            solvers.append(lambda x, f=m: np.asarray(
                dense(rt.call(f, (x,), nargout=1))).reshape(-1))

    def apply(x):
        for solve in solvers:
            x = solve(np.asarray(x).reshape(-1))
        return x
    return spla.LinearOperator((n, n), matvec=apply, dtype=float)


# ── installation ──────────────────────────────────────────────────

def _to_mat(orig):
    def convert(value):
        if isinstance(value, Sparse):
            return value.m
        return orig(value)
    return convert


def _from_mat(orig):
    def convert(value):
        if sp.issparse(value):
            return Sparse(value)
        return orig(value)
    return convert


_installed = False


def install() -> None:
    """Teach the runtime about :class:`Sparse`. Idempotent."""
    global _installed
    if _installed:
        return
    _installed = True
    lib = _mr._Library
    for name in dir(SparseLibrary):
        if name.startswith(("f_", "_krylov", "_spdiags")):
            member = getattr(SparseLibrary, name)
            setattr(lib, name, _ok(member) if name.startswith("f_")
                    else member)
    for name in _METADATA:
        _metadata(name)
    for name, impl, outs in (
            ("sum", _s_sum, False), ("abs", _s_abs, False),
            ("diag", _s_diag, False), ("find", _s_find, True),
            ("trace", _s_trace, False), ("norm", _s_norm, False),
            ("tril", _s_tril, False), ("triu", _s_triu, False),
            ("disp", _s_disp, False), ("display", _s_disp, False)):
        if hasattr(lib, f"f_{name}"):
            _overload(name, impl, outputs=outs)
    # kron may start with a full matrix and end with a sparse one
    orig_kron = getattr(lib, "f_kron", None)
    if orig_kron is not None:
        @functools.wraps(orig_kron)
        def kron(self, a, b, *rest):
            if isinstance(a, Sparse) or isinstance(b, Sparse):
                return _s_kron(self, a, b)
            return orig_kron(self, a, b, *rest)
        lib.f_kron = _ok(kron)
    for name, handler in (
            ("plus", _plus),
            ("minus", lambda rt, a, b, o: _plus(rt, a, b, o, -1)),
            ("times", _times), ("rdivide", _rdivide),
            ("ldivide", lambda rt, a, b, o: o(rt, dense(a), dense(b))),
            ("power", _power), ("mtimes", _mtimes),
            ("mldivide", _mldivide), ("mrdivide", _mrdivide),
            ("mpower", _mpower),
            ("eq", _compare(lambda x, y: x == y)),
            ("ne", _compare(lambda x, y: x != y)),
            ("lt", _compare(lambda x, y: x < y)),
            ("le", _compare(lambda x, y: x <= y)),
            ("gt", _compare(lambda x, y: x > y)),
            ("ge", _compare(lambda x, y: x >= y))):
        if hasattr(Runtime, name):
            _sparse_aware_binary(name, handler)
    _wrap_unary()
    _wrap_structure()
    _mr._to_mat = _to_mat(_mr._to_mat)
    _mr._from_mat = _from_mat(_mr._from_mat)


def _wrap_unary() -> None:
    orig_t = Runtime.transpose
    orig_u = Runtime.uminus
    orig_c = Runtime.ctranspose
    orig_not = Runtime.logical_not
    orig_truth = Runtime.truth

    def transpose(a):
        if isinstance(a, Sparse):
            return Sparse(a.m.T)
        return orig_t(a)

    def ctranspose(self, a):
        if isinstance(a, Sparse):
            return Sparse(a.m.conj().T)
        return orig_c(self, a)

    def uminus(self, a):
        if isinstance(a, Sparse):
            return Sparse(-a.m)
        return orig_u(self, a)

    def logical_not(a):
        return orig_not(dense(a))

    def truth(x):
        return orig_truth(dense(x))
    Runtime.transpose = staticmethod(transpose)
    Runtime.ctranspose = ctranspose
    Runtime.uminus = uminus
    Runtime.logical_not = staticmethod(logical_not)
    Runtime.truth = staticmethod(truth)


def _wrap_structure() -> None:
    orig_index = Runtime.index
    orig_assign = Runtime.assign
    orig_concat = Runtime.concat
    orig_call = Runtime.call
    orig_show = Runtime.show
    orig_workspace = Runtime.workspace

    def show(self, name, value):
        if isinstance(value, Sparse):
            body = "\n".join("    " + line
                             for line in sparse_text(value).splitlines())
            print(f"{name} =\n\n{body}\n")
        else:
            orig_show(self, name, value)

    def workspace(self):
        out = orig_workspace(self)
        if _seen[0]:
            out.update((k, v) for k, v in self.ns.items()
                       if isinstance(v, Sparse) and not k.startswith("_"))
        return out

    def index(self, x, args):
        if isinstance(x, Sparse):
            return _index(self, x, args)
        return orig_index(self, x, args)

    def assign(self, obj, path, value, owned=False):
        if path and path[0][0] == "()":
            if isinstance(obj, Sparse):
                return _assign(self, obj, path, value)
            if isinstance(value, Sparse):
                value = dense(value)
        return orig_assign(self, obj, path, value, owned)

    def concat(self, rows):
        if _seen[0] and any(isinstance(x, Sparse)
                                       for row in rows for x in row):
            return _concat(self, rows, orig_concat)
        return orig_concat(self, rows)

    def call(self, f, args, nargout=1, names=None):
        if _seen[0] and args \
                and getattr(f, "__self__", None) is self.lib \
                and not getattr(f, "_ml_sparse_ok", False) \
                and any(isinstance(a, Sparse) for a in args):
            args = tuple(dense(a) for a in args)
        return orig_call(self, f, args, nargout, names)
    Runtime.index = index
    Runtime.assign = assign
    Runtime.concat = concat
    Runtime.call = call
    Runtime.show = show
    Runtime.workspace = workspace
