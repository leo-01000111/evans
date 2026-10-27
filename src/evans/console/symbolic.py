"""
Symbolic maths, MATLAB's way, on SymPy.
=======================================
``syms s t`` makes symbols, and from then on ``*``, ``/``, ``^`` and the
elementary functions build formulas instead of numbers::

    syms s t
    F = laplace(exp(-2*t)*sin(3*t))      % 3/((s + 2)^2 + 9)
    f = ilaplace(1/(s*(s + 1)))          % 1 - exp(-t)
    G = subs(1/(s^2 + 2*s + 5), s, 1i)

A symbolic value is a :class:`Sym`: a SymPy expression, or a SymPy matrix
for ``[s 1; 0 s]``, wrapped so that it prints the way MATLAB prints one —
``s^2``, ``heaviside(t)``, ``[s, 1]`` — and so that the runtime can tell it
apart from a number. The runtime routes every operator with a ``Sym`` on
either side to :func:`binary`, which keeps MATLAB's distinction between
``*`` and ``.*``; the library functions with a symbolic meaning
(:data:`OVERLOADS`) take over from the numeric ones when an argument is
symbolic, and leave numbers alone.

Numbers entering a formula are made exact, as MATLAB's ``sym`` does:
``0.1`` becomes ``1/10`` and ``pi`` becomes ``pi`` (:func:`_exact`).

Not covered: symbolic functions (``syms y(t)``) and so ``dsolve``,
``ztrans``, assumptions beyond those given to ``syms``, and the Live
Editor's typeset display.
"""

from __future__ import annotations

import math
from fractions import Fraction

import numpy as np
import sympy as sp
from sympy.printing.str import StrPrinter

from .matlab_runtime import Cell, MatlabError, Struct, _as_text

#: Assumption words ``syms`` and ``sym`` accept, as SymPy keywords.
_ASSUMPTIONS = {"real": "real", "positive": "positive",
                "integer": "integer", "rational": "rational"}


# ──────────────────────────────────────────────────────────────
#  The value
# ──────────────────────────────────────────────────────────────

class Sym:
    """A symbolic scalar or matrix."""

    #: The runtime's test for a symbolic value, without importing this module.
    _ml_sym = True
    # numpy's operators defer to ours instead of making object arrays.
    __array_ufunc__ = None
    __slots__ = ("expr",)

    def __init__(self, expr) -> None:
        if isinstance(expr, sp.MatrixBase):
            expr = (expr[0, 0] if expr.shape == (1, 1)
                    else sp.ImmutableMatrix(expr))
        self.expr = expr

    @property
    def is_matrix(self) -> bool:
        return isinstance(self.expr, sp.MatrixBase)

    @property
    def shape(self) -> tuple[int, int]:
        return tuple(self.expr.shape) if self.is_matrix else (1, 1)

    def matrix(self) -> sp.ImmutableMatrix:
        return (self.expr if self.is_matrix
                else sp.ImmutableMatrix([[self.expr]]))

    def free(self) -> set:
        return set(self.expr.free_symbols)

    # ── text ────────────────────────────────────────────────────

    def __str__(self) -> str:
        return text(self)

    __repr__ = __str__

    def __hash__(self) -> int:
        return hash(self.expr)

    def __bool__(self) -> bool:
        return _truth(self.expr)

    # ── Python operators, for Python at the prompt ──────────────

    def __add__(self, o):       return binary("plus", self, o)
    def __radd__(self, o):      return binary("plus", o, self)
    def __sub__(self, o):       return binary("minus", self, o)
    def __rsub__(self, o):      return binary("minus", o, self)
    def __mul__(self, o):       return binary("mtimes", self, o)
    def __rmul__(self, o):      return binary("mtimes", o, self)
    def __truediv__(self, o):   return binary("mrdivide", self, o)
    def __rtruediv__(self, o):  return binary("mrdivide", o, self)
    def __pow__(self, o):       return binary("mpower", self, o)
    def __rpow__(self, o):      return binary("mpower", o, self)
    def __neg__(self):          return Sym(-self.expr)
    def __pos__(self):          return self
    def __eq__(self, o):        return binary("eq", self, o)
    def __ne__(self, o):        return binary("ne", self, o)
    def __lt__(self, o):        return binary("lt", self, o)
    def __le__(self, o):        return binary("le", self, o)
    def __gt__(self, o):        return binary("gt", self, o)
    def __ge__(self, o):        return binary("ge", self, o)


def is_sym(x) -> bool:
    return isinstance(x, Sym)


def _any_sym(args) -> bool:
    return any(isinstance(a, Sym) for a in args)


def _truth(expr) -> bool:
    """
    ``if`` on a symbolic value: decided only when it can be proved.

    MATLAB refuses ``if x == 1`` for a symbol ``x`` rather than guess, and
    says to use ``isAlways``; so does this.
    """
    if isinstance(expr, sp.MatrixBase):
        return all(_truth(e) for e in expr)
    decided = _decide(expr)
    if decided is None:
        raise MatlabError(
            f"Unable to prove '{_print(expr)}' literally. Use isAlways to "
            f"test the statement mathematically, or double to convert a "
            f"numeric value.")
    return decided


def _decide(expr) -> bool | None:
    """True, False, or None when it depends on the symbols."""
    if isinstance(expr, sp.Equality):
        diff = sp.simplify(expr.lhs - expr.rhs)
        if diff == 0:
            return True
        return False if diff.is_number else None
    if isinstance(expr, sp.Unequality):
        inner = _decide(sp.Eq(expr.lhs, expr.rhs))
        return None if inner is None else not inner
    if isinstance(expr, sp.core.relational.Relational):
        out = sp.simplify(expr)
        if out in (sp.true, sp.false):
            return bool(out)
        return None
    if expr in (sp.true, sp.false):
        return bool(expr)
    if expr.free_symbols:
        return None
    return bool(expr != 0)


# ──────────────────────────────────────────────────────────────
#  Conversion
# ──────────────────────────────────────────────────────────────

def _exact(v: float):
    """
    A double as the exact number it stands for, as MATLAB's ``sym(v)``.

    Tried in turn: an integer, a fraction with a modest denominator, a
    rational multiple of π, the square root of such a fraction — each only
    if it reproduces ``v`` to the last bits. Anything else is taken as the
    decimal it prints as, so ``0.123456789`` stays ``123456789/1000000000``.
    """
    if math.isnan(v):
        return sp.nan
    if math.isinf(v):
        return sp.oo if v > 0 else -sp.oo
    if v.is_integer():
        return sp.Integer(int(v))
    tol = 4 * np.finfo(float).eps * abs(v)
    q = Fraction(v).limit_denominator(1_000_000)
    if abs(float(q) - v) <= tol:
        return sp.Rational(q.numerator, q.denominator)
    q = Fraction(v / math.pi).limit_denominator(10_000)
    if q and abs(float(q) * math.pi - v) <= tol:
        return sp.Rational(q.numerator, q.denominator) * sp.pi
    if v > 0:
        q = Fraction(v * v).limit_denominator(10_000)
        if abs(math.sqrt(float(q)) - v) <= tol:
            return sp.sqrt(sp.Rational(q.numerator, q.denominator))
    return sp.Rational(repr(v))


def to_expr(x):
    """Anything the runtime holds, as a SymPy scalar or matrix."""
    if isinstance(x, Sym):
        return x.expr
    if isinstance(x, (bool, np.bool_)):
        return sp.Integer(int(x))
    if isinstance(x, (int, np.integer)):
        return sp.Integer(int(x))
    if isinstance(x, (float, np.floating)):
        return _exact(float(x))
    if isinstance(x, (complex, np.complexfloating)):
        re_, im = to_expr(float(x.real)), to_expr(float(x.imag))
        return re_ + sp.I * im
    if isinstance(x, np.ndarray):
        if x.size == 1:
            return to_expr(x.reshape(-1)[0].item())
        rows = x.reshape(1, -1) if x.ndim == 1 else x
        return sp.ImmutableMatrix([[to_expr(v) for v in row] for row in rows])
    if isinstance(x, (list, tuple)) and not isinstance(x, Cell):
        return to_expr(np.asarray(x))
    if isinstance(x, sp.Basic):
        return x
    if isinstance(x, str):
        raise MatlabError(
            f"Text '{x}' cannot be used in a formula. Use sym('{x}') or "
            f"str2sym('{x}') to make it symbolic.")
    raise MatlabError(f"A {type(x).__name__} cannot be used in a symbolic "
                      f"formula.")


def to_sym(x) -> Sym:
    return x if isinstance(x, Sym) else Sym(to_expr(x))


def to_double(x):
    """``double``: the number a symbolic value stands for."""
    if not isinstance(x, Sym):
        if isinstance(x, str):
            return np.array([float(ord(c)) for c in x])
        a = np.asarray(x)
        if a.dtype == object:
            raise MatlabError("Conversion to double is not possible.")
        out = a.astype(complex if np.iscomplexobj(a) else float)
        return out.item() if out.ndim == 0 else out
    if x.free():
        raise MatlabError(
            f"Unable to convert expression containing symbolic variables "
            f"({', '.join(sorted(str(s) for s in x.free()))}) into double "
            f"array. Substitute values first with subs.")

    def number(e):
        value = complex(sp.N(e, 17))
        return value.real if value.imag == 0 else value

    if not x.is_matrix:
        out = number(x.expr)
        return int(out) if isinstance(out, float) and out.is_integer() \
            and abs(out) < 2**53 else out
    m = x.expr
    values = [[number(m[i, j]) for j in range(m.cols)] for i in range(m.rows)]
    arr = np.array(values)
    return arr.reshape(-1) if arr.shape[0] == 1 else arr


def _symbol(name, *flags) -> sp.Symbol:
    name = _as_text(name)
    if not name.isidentifier():
        raise MatlabError(f"'{name}' is not a valid variable name.")
    kwargs = {}
    for flag in flags:
        word = _as_text(flag).lower()
        if word not in _ASSUMPTIONS:
            raise MatlabError(
                f"Unknown assumption '{_as_text(flag)}'. Use real, "
                f"positive, integer or rational.")
        kwargs[_ASSUMPTIONS[word]] = True
    return sp.Symbol(name, **kwargs)


# ──────────────────────────────────────────────────────────────
#  Printing
# ──────────────────────────────────────────────────────────────

class _MatlabPrinter(StrPrinter):
    """SymPy's text form with MATLAB's spellings: ``^``, ``heaviside``…"""

    def _print_Pow(self, expr, rational=False):
        return super()._print_Pow(expr, rational).replace("**", "^")

    def _print_ImaginaryUnit(self, expr):
        return "1i"

    def _print_Exp1(self, expr):
        return "exp(1)"

    def _print_Infinity(self, expr):
        return "Inf"

    def _print_NegativeInfinity(self, expr):
        return "-Inf"

    def _print_ComplexInfinity(self, expr):
        return "Inf"

    def _print_NaN(self, expr):
        return "NaN"

    def _print_Heaviside(self, expr):
        return f"heaviside({self._print(expr.args[0])})"

    def _print_DiracDelta(self, expr):
        if len(expr.args) > 1 and expr.args[1] != 0:
            return (f"dirac({self._print(expr.args[1])}, "
                    f"{self._print(expr.args[0])})")
        return f"dirac({self._print(expr.args[0])})"

    def _print_Abs(self, expr):
        return f"abs({self._print(expr.args[0])})"

    def _print_re(self, expr):
        return f"real({self._print(expr.args[0])})"

    def _print_im(self, expr):
        return f"imag({self._print(expr.args[0])})"

    def _print_conjugate(self, expr):
        return f"conj({self._print(expr.args[0])})"

    def _print_Relational(self, expr):
        op = {"==": "==", "!=": "~=", "<": "<", "<=": "<=", ">": ">",
              ">=": ">="}.get(expr.rel_op, expr.rel_op)
        return f"{self._print(expr.lhs)} {op} {self._print(expr.rhs)}"

    def _print_BooleanTrue(self, expr):
        return "symtrue"

    def _print_BooleanFalse(self, expr):
        return "symfalse"

    def _print_Integral(self, expr):
        f, (var, *bounds) = expr.args[0], expr.limits[0]
        tail = "".join(f", {self._print(b)}" for b in bounds)
        return f"int({self._print(f)}, {self._print(var)}{tail})"

    def _print_Derivative(self, expr):
        var, n = expr.variable_count[0]
        tail = f", {n}" if n != 1 else ""
        return f"diff({self._print(expr.expr)}, {self._print(var)}{tail})"

    def _print_LaplaceTransform(self, expr):
        f, t, s = expr.args[:3]
        return f"laplace({self._print(f)}, {self._print(t)}, {self._print(s)})"

    def _print_InverseLaplaceTransform(self, expr):
        f, s, t = expr.args[:3]
        return (f"ilaplace({self._print(f)}, {self._print(s)}, "
                f"{self._print(t)})")


_PRINTER = _MatlabPrinter()


def _print(expr) -> str:
    return _PRINTER.doprint(expr)


def text(x: Sym) -> str:
    """How MATLAB shows a symbolic value: one line, or ``[a, b]`` rows."""
    if not x.is_matrix:
        return _print(x.expr)
    m = x.expr
    if 0 in m.shape:
        return f"Empty sym: {m.rows}-by-{m.cols}"
    cells = [[_print(m[i, j]) for j in range(m.cols)] for i in range(m.rows)]
    widths = [max(len(cells[i][j]) for i in range(m.rows))
              for j in range(m.cols)]
    return "\n".join(
        "[" + ", ".join(c.ljust(w) for c, w in zip(row, widths)) + "]"
        for row in cells)


# ──────────────────────────────────────────────────────────────
#  Operators
# ──────────────────────────────────────────────────────────────

_ELEMENTWISE = {
    "plus":    lambda a, b: a + b,
    "minus":   lambda a, b: a - b,
    "times":   lambda a, b: a * b,
    "rdivide": lambda a, b: a / b,
    "ldivide": lambda a, b: b / a,
    "power":   lambda a, b: a ** b,
    "eq":      sp.Eq,
    "ne":      sp.Ne,
    "lt":      sp.Lt,
    "le":      sp.Le,
    "gt":      sp.Gt,
    "ge":      sp.Ge,
}


def _elementwise(fn, a, b):
    """``fn`` element by element, a scalar meeting a matrix as MATLAB does."""
    am, bm = isinstance(a, sp.MatrixBase), isinstance(b, sp.MatrixBase)
    if not am and not bm:
        return fn(a, b)
    if am and bm:
        if a.shape != b.shape:
            raise MatlabError(
                f"Arrays have incompatible sizes for this operation: "
                f"{a.rows}×{a.cols} and {b.rows}×{b.cols}.")
        return sp.ImmutableMatrix(a.rows, a.cols,
                                  [fn(x, y) for x, y in zip(a, b)])
    if am:
        return a.applyfunc(lambda x: fn(x, b))
    return b.applyfunc(lambda y: fn(a, y))


def binary(op: str, a, b) -> Sym:
    """One MATLAB operator with a symbolic operand, by its function name."""
    A, B = to_expr(a), to_expr(b)
    am, bm = isinstance(A, sp.MatrixBase), isinstance(B, sp.MatrixBase)
    if op in _ELEMENTWISE:
        return Sym(_elementwise(_ELEMENTWISE[op], A, B))
    if op == "mtimes":
        if am and bm:
            if A.cols != B.rows:
                raise MatlabError(
                    f"Incorrect dimensions for matrix multiplication: "
                    f"{A.rows}×{A.cols} * {B.rows}×{B.cols}. Use .* for "
                    f"elementwise multiplication.")
            return Sym(A * B)
        return Sym(_elementwise(lambda x, y: x * y, A, B))
    if op == "mrdivide":
        if bm:
            if not am or A.cols != B.cols:
                raise MatlabError("Matrix dimensions must agree.")
            return Sym(A * B.inv())
        return Sym(_elementwise(lambda x, y: x / y, A, B))
    if op == "mldivide":
        if am:
            if not bm or A.rows != B.rows:
                raise MatlabError("Matrix dimensions must agree.")
            return Sym(A.inv() * B)
        return Sym(_elementwise(lambda x, y: y / x, A, B))
    if op == "mpower":
        if am:
            if A.rows != A.cols:
                raise MatlabError("For a vector, use .^ for elementwise "
                                  "power.")
            return Sym(A ** B)
        if bm:
            raise MatlabError("A scalar raised to a matrix power is not "
                              "supported for symbolic values.")
        return Sym(A ** B)
    raise MatlabError(f"The operator {op} is not defined for symbolic "
                      f"values.")


def transpose(x: Sym, conjugate: bool) -> Sym:
    if not x.is_matrix:
        return Sym(sp.conjugate(x.expr)) if conjugate else x
    return Sym(x.expr.H if conjugate else x.expr.T)


def concat(rows: list[list]) -> Sym:
    """``[a b; c d]`` with any symbolic piece: one symbolic matrix."""
    blocks = []
    for row in rows:
        parts = []
        for v in row:
            e = to_expr(v)
            m = e if isinstance(e, sp.MatrixBase) else sp.ImmutableMatrix([[e]])
            if 0 not in m.shape:
                parts.append(m)
        if parts:
            try:
                blocks.append(sp.Matrix.hstack(*parts))
            except sp.ShapeError:
                raise MatlabError("Dimensions of arrays being concatenated "
                                  "are not consistent.") from None
    if not blocks:
        return Sym(sp.ImmutableMatrix(0, 0, []))
    try:
        return Sym(sp.Matrix.vstack(*blocks))
    except sp.ShapeError:
        raise MatlabError("Dimensions of arrays being concatenated are not "
                          "consistent.") from None


def as_objects(x: Sym) -> np.ndarray:
    """The matrix as a numpy object array, so the runtime can index it."""
    m = x.matrix()
    arr = np.empty(m.shape, dtype=object)
    for i in range(m.rows):
        for j in range(m.cols):
            arr[i, j] = m[i, j]
    return arr


def from_objects(value) -> Sym:
    """The runtime's indexing result back as a symbolic value."""
    if isinstance(value, np.ndarray):
        rows = value.reshape(1, -1) if value.ndim == 1 else value
        return Sym(sp.ImmutableMatrix(rows.tolist()))
    return Sym(value)


def columns(x: Sym) -> list[Sym]:
    """What ``for v = X`` steps through: the columns."""
    m = x.matrix()
    return [Sym(m[:, j]) for j in range(m.cols)]


# ──────────────────────────────────────────────────────────────
#  Variables
# ──────────────────────────────────────────────────────────────

def _sort_key(sym) -> tuple:
    return (str(sym).lower(), str(sym))


def symvar(x, n: int | None = None) -> list:
    """
    The symbols in ``x``: alphabetical, or with ``n`` the ``n`` closest to
    ``x`` — MATLAB's rule for picking the default variable, so ``diff(a*t^2)``
    differentiates by ``t``, not ``a``.
    """
    found = sorted(to_expr(x).free_symbols, key=_sort_key)
    if n is None:
        return found

    def closeness(sym):
        c = str(sym)[0].lower()
        gap = abs(ord(c) - ord("x"))
        return (gap, -ord(c), str(sym))
    return sorted(found, key=closeness)[:n]


def _default_var(expr, preferred=None):
    if preferred is not None:
        for sym in expr.free_symbols:
            if str(sym) == preferred:
                return sym
    picked = symvar(Sym(expr), 1)
    return picked[0] if picked else sp.Symbol(preferred or "x")


def _as_var(v):
    if isinstance(v, str):
        return sp.Symbol(v)
    e = to_expr(v)
    if isinstance(e, sp.Symbol):
        return e
    raise MatlabError(f"'{text(to_sym(v))}' is not a symbolic variable.")


def _is_var(v) -> bool:
    return isinstance(v, Sym) and isinstance(v.expr, sp.Symbol)


def _map(x: Sym, fn) -> Sym:
    """``fn`` on a scalar, or on every element of a matrix."""
    return Sym(x.expr.applyfunc(fn) if x.is_matrix else fn(x.expr))


# ──────────────────────────────────────────────────────────────
#  The functions
# ──────────────────────────────────────────────────────────────
# Each takes the runtime first (most ignore it) and the MATLAB arguments
# after. An entry in OVERLOADS replaces the numeric function of that name
# when any argument is symbolic; a NEW one is the only definition there is.

def syms(rt, *args, nargout=0):
    """``syms s t``, ``syms x real``: make symbols in the workspace."""
    words = [_as_text(a) for a in args]
    if not words:
        names = sorted(n for n, v in rt.ns.items()
                       if isinstance(v, Sym) and not n.startswith("_"))
        if nargout:
            return Cell(names)
        print("  ".join(names) if names else "")
        return None
    flags = []
    while words and words[-1].lower() in (*_ASSUMPTIONS, "clear"):
        flags.insert(0, words.pop())
    flags = [f for f in flags if f.lower() != "clear"]
    if not words:
        raise MatlabError("syms needs at least one variable name.")
    made = []
    for word in words:
        if "(" in word:
            raise MatlabError(
                f"Symbolic functions such as syms {word} are not supported "
                f"in Evans, and nor is dsolve. Use laplace and ilaplace to "
                f"solve a linear ODE.")
        sym = Sym(_symbol(word, *flags))
        rt.ns[word] = sym
        made.append(sym)
    if nargout:
        return Cell(made)
    return None


def sym(rt, x, *flags):
    """``sym('x')``, ``sym(1/3)``, ``sym('a', [1 3])``."""
    if isinstance(x, str):
        if flags and not isinstance(flags[0], str):
            return _sym_array(x, flags[0], flags[1:])
        if x.isidentifier():
            return Sym(_symbol(x, *flags))
        return str2sym(rt, x)
    return to_sym(x)


def _sym_array(name: str, dims, flags) -> Sym:
    shape = [int(d) for d in np.atleast_1d(dims)]
    rows, cols = (shape[0], shape[0]) if len(shape) == 1 else shape[:2]
    if rows == 1 or cols == 1:
        names = [[f"{name}{k + 1}" for k in range(cols)]] if rows == 1 else \
            [[f"{name}{k + 1}"] for k in range(rows)]
    else:
        names = [[f"{name}{i + 1}_{j + 1}" for j in range(cols)]
                 for i in range(rows)]
    return Sym(sp.ImmutableMatrix(
        [[_symbol(n, *flags) for n in row] for row in names]))


#: MATLAB's names for the functions SymPy spells differently.
_PARSE_NAMES = {"heaviside": sp.Heaviside, "dirac": sp.DiracDelta,
                "abs": sp.Abs, "conj": sp.conjugate, "real": sp.re,
                "imag": sp.im, "log": sp.log, "exp": sp.exp,
                "sqrt": sp.sqrt, "pi": sp.pi, "Inf": sp.oo, "inf": sp.oo,
                "i": sp.I, "j": sp.I, "asin": sp.asin, "acos": sp.acos,
                "atan": sp.atan}


def str2sym(rt, source):
    """``str2sym('s^2 + 2*s + 1')``: read a formula from text."""
    from sympy.parsing.sympy_parser import (
        convert_xor,
        implicit_multiplication,
        parse_expr,
        standard_transformations,
    )
    text_ = _as_text(source).replace(".^", "^").replace(".*", "*") \
        .replace("./", "/").replace("~=", "!=")
    names = dict(_PARSE_NAMES)
    for name, value in rt.ns.items():
        if isinstance(value, Sym) and not value.is_matrix:
            names[name] = value.expr
    try:
        expr = parse_expr(
            text_, local_dict=names,
            transformations=(*standard_transformations, convert_xor,
                             implicit_multiplication))
    except Exception as exc:                            # noqa: BLE001
        raise MatlabError(f"Unable to read '{_as_text(source)}' as a "
                          f"formula: {exc}") from None
    return Sym(expr)


def laplace(rt, f, *vars_):
    """
    ``laplace(f)``, ``laplace(f, transVar)``, ``laplace(f, var, transVar)``.

    The defaults are MATLAB's: ``t`` to ``s``, or ``s`` to ``z`` when ``f``
    is a function of ``s``. ``var`` keeps the assumptions it has: making it
    positive for the transform, as :func:`ilaplace` does for its result,
    would turn ``dirac(t)`` into 0 before it was ever integrated.
    """
    f = to_sym(f)
    if len(vars_) > 2:
        raise MatlabError("Too many input arguments.")
    var = _as_var(vars_[0]) if len(vars_) == 2 else _default_var(f.expr, "t")
    trans = (_as_var(vars_[-1]) if vars_ else
             sp.Symbol("z" if str(var) == "s" else "s"))

    def one(e):
        return _tidy(sp.laplace_transform(e, var, trans, noconds=True))
    return _map(f, one)


def ilaplace(rt, F, *vars_):
    """
    ``ilaplace(F)``, ``ilaplace(F, transVar)``, ``ilaplace(F, var, transVar)``.

    Defaults ``s`` to ``t`` (``x`` when ``F`` is a function of ``t``). The
    result is for ``t > 0``, as MATLAB gives it: no ``heaviside(t)`` factor.
    """
    F = to_sym(F)
    if len(vars_) > 2:
        raise MatlabError("Too many input arguments.")
    var = _as_var(vars_[0]) if len(vars_) == 2 else _default_var(F.expr, "s")
    trans = (_as_var(vars_[-1]) if vars_ else
             sp.Symbol("x" if str(var) == "t" else "t"))
    tp = sp.Dummy(str(trans), positive=True)

    def one(e):
        out = sp.inverse_laplace_transform(e, var, tp)
        return _tidy(out.subs(tp, trans))
    return _map(F, one)


def _tidy(e):
    """Light clean-up of a transform: no ``Heaviside(t)`` for ``t > 0``."""
    try:
        return sp.simplify(e) if sp.count_ops(e) < 60 else e
    except Exception:                                   # noqa: BLE001
        return e


def simplify(rt, f, *_options):
    return _map(to_sym(f), sp.simplify)


def expand(rt, f, *_options):
    return _map(to_sym(f), sp.expand)


def factor(rt, f, *vars_):
    """``factor(f)`` symbolically; ``factor(n)`` the prime factors of ``n``."""
    if not isinstance(f, Sym):
        n = int(to_double(f))
        if n < 1:
            raise MatlabError("factor needs a positive integer.")
        primes = [p for p, k in sorted(sp.factorint(n).items())
                  for _ in range(k)] or [n]
        return np.array(primes, dtype=float)
    if vars_:
        gens = [_as_var(v) for v in vars_]
        return _map(f, lambda e: sp.factor(e, *gens))
    return _map(f, sp.factor)


def collect(rt, f, var=None):
    f = to_sym(f)
    v = _as_var(var) if var is not None else _default_var(f.expr)
    return _map(f, lambda e: sp.collect(sp.expand(e), v))


def partfrac(rt, f, var=None, *_options):
    f = to_sym(f)
    v = _as_var(var) if var is not None else _default_var(f.expr)
    return _map(f, lambda e: sp.apart(sp.together(e), v))


def numden(rt, f, nargout=1):
    """
    ``[N, D] = numden(f)``: numerator and denominator over a common one,
    with common factors cancelled, so the two are coprime as in MATLAB.
    """
    f = to_sym(f)
    if f.is_matrix:
        parts = [sp.fraction(sp.cancel(sp.together(e))) for e in f.expr]
        n = Sym(sp.ImmutableMatrix(f.expr.rows, f.expr.cols,
                                   [p[0] for p in parts]))
        d = Sym(sp.ImmutableMatrix(f.expr.rows, f.expr.cols,
                                   [p[1] for p in parts]))
    else:
        num, den = sp.fraction(sp.cancel(sp.together(f.expr)))
        n, d = Sym(sp.expand(num)), Sym(sp.expand(den))
    return (n, d) if nargout >= 2 else n


def sym2poly(rt, p):
    """Coefficients of a polynomial, highest power first, as numbers."""
    p = to_sym(p)
    if p.is_matrix:
        raise MatlabError("sym2poly needs a scalar polynomial.")
    free = sorted(p.free(), key=_sort_key)
    if len(free) > 1:
        raise MatlabError(
            f"sym2poly needs a polynomial in one variable; this one has "
            f"{', '.join(map(str, free))}.")
    if not free:
        return float(to_double(p))
    try:
        coeffs = sp.Poly(sp.expand(p.expr), free[0]).all_coeffs()
    except sp.PolynomialError:
        raise MatlabError(f"'{p}' is not a polynomial in {free[0]}. Use "
                          f"numden first for a ratio.") from None
    return np.array([to_double(Sym(c)) for c in coeffs], dtype=float)


def poly2sym(rt, c, var=None):
    v = _as_var(var) if var is not None else sp.Symbol("x")
    e = to_expr(c)
    coeffs = list(e) if isinstance(e, sp.MatrixBase) else [e]
    n = len(coeffs) - 1
    return Sym(sp.Add(*[k * v ** (n - i) for i, k in enumerate(coeffs)]))


def subs(rt, f, *args):
    """
    ``subs(f)``, ``subs(f, new)``, ``subs(f, old, new)``.

    ``old`` and ``new`` may be single values, or cells or arrays of them
    paired off. With no ``old``, ``new`` replaces the default variable;
    with neither, every symbol in ``f`` named after a workspace variable
    that holds something else takes that variable's value.
    """
    f = to_sym(f)
    if len(args) > 2:
        raise MatlabError("Too many input arguments.")
    if not args:
        pairs = []
        for symbol in f.free():
            value = rt.ns.get(str(symbol))
            if value is None or (isinstance(value, Sym)
                                 and value.expr == symbol):
                continue
            if isinstance(value, (Sym, int, float, complex, np.ndarray,
                                  np.number, bool)):
                pairs.append((symbol, to_expr(value)))
    elif len(args) == 1:
        pairs = [(_default_var(f.expr), to_expr(args[0]))]
    elif len(_items(args[0])) == 1:
        # One variable, and a value or an array of values for it.
        old = _items(args[0])[0]
        pairs = [(_as_var(old) if isinstance(old, str) else to_expr(old),
                  to_expr(args[1]))]
    else:
        olds, news = _items(args[0]), _items(args[1])
        if len(olds) != len(news):
            if len(news) == 1:
                news = news * len(olds)
            else:
                raise MatlabError("subs: old and new must have the same "
                                  "number of elements.")
        pairs = [(_as_var(o) if isinstance(o, str) else to_expr(o),
                  to_expr(n)) for o, n in zip(olds, news)]
    if not pairs:
        return f
    matrix_new = [p for p in pairs if isinstance(p[1], sp.MatrixBase)]
    if matrix_new:
        if f.is_matrix or len(pairs) > 1:
            raise MatlabError("subs: a matrix can replace one variable of a "
                              "scalar formula only.")
        old, new = pairs[0]
        return Sym(new.applyfunc(lambda v: f.expr.subs(old, v)))
    return _map(f, lambda e: e.subs(pairs, simultaneous=True))


def _items(x) -> list:
    if isinstance(x, Cell):
        return list(x)
    if isinstance(x, Sym) and x.is_matrix:
        return [Sym(e) for e in x.expr]
    if isinstance(x, np.ndarray) and x.size > 1:
        return [v.item() for v in x.reshape(-1)]
    return [x]


def diff(rt, f, *args):
    """``diff(f)``, ``diff(f, n)``, ``diff(f, var)``, ``diff(f, var, n)``."""
    f = to_sym(f)
    var, n = None, 1
    for a in args:
        if _is_var(a) or isinstance(a, str):
            var = _as_var(a)
        else:
            n = int(to_double(a))
    if var is None:
        var = _default_var(f.expr)
    return _map(f, lambda e: sp.diff(e, var, n))


def integrate(rt, f, *args):
    """``int(f)``, ``int(f, var)``, ``int(f, a, b)``, ``int(f, var, a, b)``."""
    f = to_sym(f)
    args = [a for a in args if not isinstance(a, str) or _as_text(a)
            .isidentifier() and a not in ("IgnoreAnalyticConstraints",
                                          "PrincipalValue", "Hold")]
    var = None
    if args and (_is_var(args[0]) or isinstance(args[0], str)):
        var = _as_var(args.pop(0))
    if var is None:
        var = _default_var(f.expr)
    if len(args) == 2:
        a, b = to_expr(args[0]), to_expr(args[1])
        return _map(f, lambda e: sp.integrate(e, (var, a, b)))
    if args:
        raise MatlabError("int takes a variable and two bounds: "
                          "int(f, x, a, b).")
    return _map(f, lambda e: sp.integrate(e, var))


def limit(rt, f, *args):
    """``limit(f, var, a)``, ``limit(f, a)``, ``…, 'left'`` or ``'right'``."""
    f = to_sym(f)
    side = "+-"
    rest = []
    for a in args:
        if isinstance(a, str) and a.lower() in ("left", "right"):
            side = "-" if a.lower() == "left" else "+"
        else:
            rest.append(a)
    var, point = None, sp.Integer(0)
    if len(rest) == 2:
        var, point = _as_var(rest[0]), to_expr(rest[1])
    elif len(rest) == 1:
        point = to_expr(rest[0])
    if var is None:
        var = _default_var(f.expr)
    if point in (sp.oo, -sp.oo):
        side = "-" if point == sp.oo else "+"

    def one(e):
        try:
            out = sp.limit(e, var, point, dir=side)
        except ValueError:                  # the one-sided limits differ
            return sp.nan
        # Two-sided 1/x is +Inf from one side and -Inf from the other: SymPy
        # calls that complex infinity, MATLAB calls it NaN.
        return sp.nan if out is sp.zoo and side == "+-" else out
    return _map(f, one)


def taylor(rt, f, *args):
    """``taylor(f, var, a, 'Order', n)``: the series to order ``n - 1``."""
    f = to_sym(f)
    order, rest = 6, []
    items = list(args)
    while items:
        a = items.pop(0)
        if isinstance(a, str) and a.lower() == "order" and items:
            order = int(to_double(items.pop(0)))
        elif isinstance(a, str) and a.lower() == "expansionpoint" and items:
            rest.append(items.pop(0))
        else:
            rest.append(a)
    var, point = None, sp.Integer(0)
    for a in rest:
        if var is None and (_is_var(a) or isinstance(a, str)):
            var = _as_var(a)
        else:
            point = to_expr(a)
    if var is None:
        var = _default_var(f.expr)
    return _map(f, lambda e: sp.series(e, var, point, order).removeO())


def solve(rt, *args, nargout=1):
    """
    ``solve(eqn, var)``, ``solve(eqn1, eqn2, var1, var2)``.

    An expression without ``==`` means ``expression == 0``. One variable
    gives a column of solutions; several give a struct with a field for
    each, or one output each with ``[x, y] = solve(…)``.
    """
    items = []
    skip = False
    for i, a in enumerate(args):
        if skip:
            skip = False
            continue
        if isinstance(a, str) and i + 1 < len(args) and not \
                isinstance(args[i + 1], str) and a[:1].isupper():
            skip = True                        # 'Real', true and the like
            continue
        items.append(a)
    if not items:
        raise MatlabError("solve needs an equation.")
    eqs, vars_ = [], []
    for k, a in enumerate(items):
        if k > 0 and (isinstance(a, str) or _is_var(a)
                      or (isinstance(a, Sym) and a.is_matrix and all(
                          isinstance(e, sp.Symbol) for e in a.expr))):
            vars_ += ([_as_var(a)] if not (isinstance(a, Sym) and a.is_matrix)
                      else list(a.expr))
        else:
            e = to_expr(a)
            eqs += list(e) if isinstance(e, sp.MatrixBase) else [e]
    eqs = [sp.Eq(e.lhs, e.rhs) if isinstance(e, sp.Equality) else e
           for e in eqs]
    if not vars_:
        joined = sp.ImmutableMatrix([[e if not isinstance(e, sp.Equality)
                                      else e.lhs - e.rhs for e in eqs]])
        # Picked by closeness to x, returned alphabetically, as MATLAB.
        vars_ = sorted(symvar(Sym(joined), len(eqs) if len(eqs) > 1 else 1),
                       key=_sort_key)
    if not vars_:
        raise MatlabError("solve: the equation has no symbolic variable.")
    found = sp.solve(eqs, vars_, dict=True)

    def column(var):
        values = [d.get(var, var) for d in found]
        if len(values) == 1:
            return Sym(values[0])
        return Sym(sp.ImmutableMatrix(len(values), 1, values))

    if len(vars_) == 1:
        return column(vars_[0])
    if nargout >= 2:
        return tuple(column(v) for v in vars_[:nargout])
    return Struct({str(v): column(v) for v in vars_})


def vpa(rt, x, digits=32):
    return _map(to_sym(x), lambda e: sp.N(e, int(to_double(digits))))


def pretty(rt, x):
    print(sp.pretty(to_expr(x), use_unicode=True))


def latex(rt, x):
    return sp.latex(to_expr(x))


def char(rt, x, *_):
    return text(x)


def is_always(rt, cond, *_options):
    x = to_sym(cond)
    if x.is_matrix:
        return np.array([[bool(_decide(e)) for e in row]
                         for row in x.expr.tolist()])
    return bool(_decide(x.expr))


def double(rt, x):
    return to_double(x)


def heaviside(rt, x):
    """The unit step; ``heaviside(0)`` is 1/2, as in MATLAB."""
    if isinstance(x, Sym):
        return _map(x, lambda e: sp.Heaviside(e, sp.S.Half))
    a = np.asarray(x, dtype=float)
    out = np.heaviside(a, 0.5)
    return out.item() if out.ndim == 0 else out


def dirac(rt, *args):
    """``dirac(x)`` or ``dirac(n, x)``: Inf at 0, else 0, for numbers."""
    n, x = (args[0], args[1]) if len(args) == 2 else (0, args[0])
    if isinstance(x, Sym) or isinstance(n, Sym):
        k = int(to_double(n))
        return _map(to_sym(x), lambda e: sp.DiracDelta(e, k) if k
                    else sp.DiracDelta(e))
    a = np.asarray(x, dtype=float)
    out = np.where(a == 0, np.inf, 0.0)
    return out.item() if out.ndim == 0 else out


def det(rt, a):
    return Sym(_square(a).det())


def inv(rt, a):
    m = _square(a)
    if m.det() == 0:
        raise MatlabError("The matrix is singular.")
    return Sym(sp.simplify(m.inv()))


def _square(a):
    m = to_sym(a).matrix()
    if m.rows != m.cols:
        raise MatlabError("Matrix must be square.")
    return m


def matlab_function(rt, f, *options):
    """
    ``h = matlabFunction(f)``: a function handle that evaluates ``f`` on
    numbers, arrays included, with the variables in alphabetical order —
    or in the order given by ``'Vars', {t, a}``.
    """
    f = to_sym(f)
    order = symvar(f)
    items = list(options)
    while items:
        key = items.pop(0)
        if isinstance(key, str) and key.lower() == "vars" and items:
            order = [_as_var(v) for v in _items(items.pop(0))]
    fn = sp.lambdify(order, f.expr, modules=[{"Heaviside": _np_heaviside},
                                             "numpy"])

    def handle(*values):
        if len(values) != len(order):
            raise MatlabError(
                f"This function takes {len(order)} input(s) "
                f"({', '.join(map(str, order))}), got {len(values)}.")
        out = fn(*[np.asarray(v, dtype=float) if not np.iscomplexobj(v)
                   else np.asarray(v) for v in values])
        out = np.asarray(out)
        if values and out.ndim == 0 and np.ndim(values[0]) > 0:
            out = np.full(np.shape(values[0]), out.item())
        return out.item() if out.ndim == 0 else out

    handle._ml_function = True
    handle.__name__ = "matlabFunction"
    handle.matlab = "@(" + ",".join(map(str, order)) + ") " + text(f)
    return handle


def _np_heaviside(x, h0=0.5):
    return np.heaviside(x, float(h0))


def fplot(rt, f, *args):
    """
    ``fplot(f)``, ``fplot(f, [a b])``, ``fplot(f, [a b], 'r--')``: plot a
    symbolic expression of one variable, or a function handle, over an
    interval — by default ``[-5 5]``, as in MATLAB.
    """
    rest = list(args)
    lo, hi = -5.0, 5.0
    if rest and not isinstance(rest[0], str):
        bounds = np.atleast_1d(to_double(rest.pop(0))).astype(float)
        if bounds.size != 2:
            raise MatlabError("fplot: the interval must be [a b].")
        lo, hi = float(bounds[0]), float(bounds[1])
    x = np.linspace(lo, hi, 600)
    if isinstance(f, Sym):
        if len(f.free()) > 1:
            raise MatlabError(
                f"fplot needs an expression in one variable; this one has "
                f"{', '.join(sorted(map(str, f.free())))}. Use subs first.")
        handle = matlab_function(rt, f)
        y = handle(x) if f.free() else np.full_like(x, to_double(f))
    else:
        y = rt.call(f, (x,), nargout=1)
    y = np.asarray(y)
    if np.iscomplexobj(y):
        y = np.where(np.abs(y.imag) < 1e-12, y.real, np.nan)
    rt.lib.f_plot(x, np.asarray(y, dtype=float), *rest)


#: Elementwise functions: MATLAB name → SymPy function.
_ELEMENTARY = {
    "exp": sp.exp, "log": sp.log, "sqrt": sp.sqrt, "abs": sp.Abs,
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan, "asin": sp.asin,
    "acos": sp.acos, "atan": sp.atan, "sinh": sp.sinh, "cosh": sp.cosh,
    "tanh": sp.tanh, "sign": sp.sign, "real": sp.re, "imag": sp.im,
    "conj": sp.conjugate,
    "log10": lambda e: sp.log(e, 10), "log2": lambda e: sp.log(e, 2),
}


def _elementary(fn):
    def apply(rt, x):
        return _map(to_sym(x), fn)
    return apply


#: Functions that replace the numeric one of the same name when an argument
#: is symbolic.
OVERLOADS = {
    **{name: _elementary(fn) for name, fn in _ELEMENTARY.items()},
    "diff": diff, "det": det, "inv": inv,
    "char": char, "string": char,
}

#: Functions only the symbolic side has. ``int`` is spelled ``integrate``
#: here only because ``int`` is Python's.
NEW = {
    "syms": syms, "sym": sym, "str2sym": str2sym,
    "laplace": laplace, "ilaplace": ilaplace,
    "simplify": simplify, "expand": expand, "factor": factor,
    "collect": collect,
    "partfrac": partfrac, "numden": numden, "subs": subs,
    "int": integrate, "limit": limit, "taylor": taylor, "solve": solve,
    "sym2poly": sym2poly, "poly2sym": poly2sym,
    "symvar": lambda rt, x, n=None: Sym(sp.ImmutableMatrix(
        [symvar(x, None if n is None else int(to_double(n)))])),
    "vpa": vpa, "pretty": pretty, "latex": latex, "isAlways": is_always,
    "double": double, "heaviside": heaviside, "dirac": dirac,
    "matlabFunction": matlab_function, "fplot": fplot,
}
#: The ones that count their outputs.
COUNTS_OUTPUTS = {"numden", "solve", "syms"}
