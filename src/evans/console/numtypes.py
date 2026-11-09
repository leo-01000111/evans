"""
Integer and single types.
=========================
MATLAB's ``int8`` … ``uint64`` and ``single``, on numpy's own integer and
float32 dtypes. A value is of one of these classes exactly when it is a numpy
integer scalar or array, or a float32 one. Everything else numeric is
``double`` (a Python number or a float64 array) or ``logical`` (bool).

Arithmetic is done in double and then cast back, with MATLAB's rules: round
half away from zero, saturate at the type's limits, ``NaN`` becomes 0. Two
different integer classes cannot meet in an operator; an integer meets a
double or a single and stays an integer.

The library functions know nothing of this: :func:`finish` runs after each
call and turns any integer a function leaked (``find`` returns numpy
``int64``) back into a double, unless the function is one of those that keep
their input's class (``sum``, ``abs``, ``max`` …) or builds a typed value.
"""

from __future__ import annotations

import numpy as np

INT_NAMES = ("int8", "int16", "int32", "int64",
             "uint8", "uint16", "uint32", "uint64")
INTS = {n: np.dtype(n) for n in INT_NAMES}
_BY_DTYPE = {dt: n for n, dt in INTS.items()}
_SINGLE = np.dtype("float32")

#: Functions whose result has the class of their numeric input.
KEEP = frozenset("""
abs sum prod cumsum cumprod max min sort unique flip fliplr flipud reshape
repmat diag mod rem floor ceil round fix sign real imag conj diff circshift
triu tril horzcat vertcat cat transpose ctranspose fftshift ifftshift
idivide bitand bitor bitxor bitshift bitcmp
""".split())

#: Functions that run on the values in double, then cast back (so ``abs`` of
#: ``int8(-128)`` saturates instead of wrapping).
COMPUTE = frozenset("""
abs sum prod cumsum cumprod mod rem diff sign real imag conj floor ceil
round fix
""".split())

#: Functions that make typed values out of untyped inputs.
BUILD = frozenset(list(INT_NAMES) + """
single double logical cast zeros ones eye intmax intmin realmax realmin
flintmax eps typecast audioread
""".split())


def num_class(x) -> str | None:
    """The integer or single class name of ``x``, else ``None``."""
    if isinstance(x, (np.ndarray, np.generic)):
        dt = x.dtype
        if dt in _BY_DTYPE:
            return _BY_DTYPE[dt]
        if dt == _SINGLE or dt == np.dtype("complex64"):
            return "single"
    return None


def is_typed(x) -> bool:
    return num_class(x) is not None


def is_int(x) -> bool:
    return num_class(x) in INTS


def dominant(values) -> str | None:
    """The class an operation on ``values`` yields (the first integer wins)."""
    classes = [num_class(v) for v in values]
    for c in classes:
        if c in INTS:
            return c
    return "single" if "single" in classes else None


def check_pair(a, b, opname: str = "+") -> str | None:
    """The result class of ``a op b``; two integer classes are an error."""
    from .matlab_runtime import MatlabError
    ca, cb = num_class(a), num_class(b)
    if ca in INTS and cb in INTS and ca != cb:
        raise MatlabError(
            f"Binary operator '{opname}' not supported for integer classes "
            f"'{ca}' and '{cb}'. Integers can only be combined with "
            f"integers of the same class, or scalars of type double.",
            "MATLAB:UndefinedFunction")
    return dominant((a, b))


def to_double(x):
    """``x`` as float64 (or complex128), for arithmetic done in double."""
    if isinstance(x, np.ndarray):
        return x.astype(complex if np.iscomplexobj(x) else float)
    if isinstance(x, np.generic):
        return complex(x) if np.iscomplexobj(x) else float(x)
    return x


def _round_away(f):
    return np.trunc(f + np.copysign(0.5, f))


def cast(x, name: str):
    """``x`` converted to class ``name`` the way MATLAB does it."""
    if name == "double":
        a = np.asarray(x)
        if a.dtype == bool or a.dtype.kind in "iuf":
            a = a.astype(float)
        elif a.dtype.kind == "c":
            a = a.astype(complex)
        return a.item() if a.ndim == 0 else a
    a = np.asarray(x)
    if a.dtype.kind == "U":
        a = np.array([ord(c) for c in str(a)], dtype=float)
    if a.dtype == object:
        a = a.astype(float)
    if name == "single":
        out = a.astype(np.complex64 if a.dtype.kind == "c" else np.float32)
        return out[()] if out.ndim == 0 else out
    dt = INTS[name]
    info = np.iinfo(dt)
    if a.dtype.kind in "iu":
        lo, hi = int(info.min), int(info.max)
        if a.dtype.itemsize <= 4 and dt.itemsize <= 4:
            out = np.clip(a.astype(np.int64), lo, hi).astype(dt)
        else:
            flat = [min(max(int(v), lo), hi) for v in a.reshape(-1)]
            out = np.array(flat, dtype=dt).reshape(a.shape)
    else:
        f = a.real.astype(float) if a.dtype.kind == "c" else a.astype(float)
        f = np.where(np.isnan(f), 0.0, _round_away(f))
        lo, hi = float(info.min), float(info.max)
        over = f >= hi
        under = f <= lo
        safe = np.where(over | under, 0.0, f)
        out = safe.astype(dt)
        out = np.where(over, info.max, np.where(under, info.min, out)) \
            .astype(dt)
    return out[()] if out.ndim == 0 else out


def plain(x):
    """What a library function leaked, back to a double."""
    if isinstance(x, np.generic):
        if x.dtype in _BY_DTYPE:
            return int(x)
        if x.dtype == _SINGLE:
            return float(x)
    elif isinstance(x, np.ndarray):
        if x.dtype in _BY_DTYPE or x.dtype == _SINGLE:
            return x.astype(float)
    elif type(x) is tuple:
        return tuple(plain(v) for v in x)
    return x


def finish(name: str, args: tuple, result):
    """
    Settle the class of a library function's result: see the module's
    docstring.
    """
    if name in BUILD:
        return result
    typed = [a for a in args if is_typed(a)]
    if not typed:
        return plain(result)
    if name in KEEP:
        cls = dominant(typed)
        if type(result) is tuple:
            return (_keep(result[0], cls),) + tuple(
                plain(r) for r in result[1:])
        return _keep(result, cls)
    return plain(result)


def _keep(value, cls: str):
    if isinstance(value, (np.ndarray, np.generic, int, float, complex)) \
            and not isinstance(value, (bool, np.bool_)):
        if isinstance(value, np.ndarray) and value.dtype == bool:
            return value
        return cast(value, cls)
    return value


def intlimits(name: str) -> tuple[int, int]:
    info = np.iinfo(INTS[name])
    return int(info.min), int(info.max)
