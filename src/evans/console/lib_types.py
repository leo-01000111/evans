"""
Numeric classes and string arrays.
==================================
``int8`` … ``uint64``, ``single``, ``double``, ``logical``, ``cast``,
``intmax`` and friends, the bit functions, and ``string`` / ``strlength`` for
``"…"`` strings. The rules for arithmetic and display live in
:mod:`.numtypes` and :mod:`.matlab_runtime`.

A mixin of :class:`.matlab_runtime._Library`: each ``f_<name>`` method is the
MATLAB function ``<name>``. Import :mod:`.matlab_runtime` first, never this
module on its own: the two import each other.
"""

from __future__ import annotations

import numpy as np

from . import matlab_runtime as _mr  # noqa: F401
from . import numtypes as nt
from .matlab_runtime import (
    Cell,
    MatlabError,
    Str,
    StrArray,
    _as_array,
    _normalise,
    _number,
    _strarray,
)


def _converter(name: str):
    def convert(self, x=0):
        if isinstance(x, StrArray) or isinstance(x, Cell):
            raise MatlabError(f"Conversion to {name} from "
                              f"{self.f_class(x)} is not possible.")
        if isinstance(x, str):
            x = np.array([ord(c) for c in x], dtype=float)
        return _normalise(np.asarray(nt.cast(x, name))) \
            if np.ndim(x) else nt.cast(x, name)
    convert.__name__ = f"f_{name}"
    convert.__doc__ = f"``{name}(x)``: ``x`` as class {name}."
    return convert


def _bits(a) -> tuple[np.ndarray, str | None]:
    """The operand of a bit function as an unsigned/signed integer array."""
    cls = nt.num_class(a)
    arr = np.asarray(a)
    if cls in nt.INTS:
        return arr, cls
    if arr.dtype == bool:
        return arr.astype(np.uint64), None
    if np.any(arr < 0) or np.any(arr != np.round(arr)):
        raise MatlabError("Inputs must be non-negative integers.")
    return arr.astype(np.uint64), None


class TypesLibrary:
    """Mixed into ``_Library``."""

    for _n in nt.INT_NAMES + ("single",):
        locals()[f"f_{_n}"] = _converter(_n)
    del _n

    def f_double(self, x=0):
        if isinstance(x, str):
            x = np.array([ord(c) for c in x], dtype=float)
        out = nt.cast(x, "double")
        return _normalise(out) if isinstance(out, np.ndarray) else out

    def f_logical(self, x=0):
        a = np.asarray(x)
        if a.dtype.kind == "f" and np.any(np.isnan(a)):
            raise MatlabError("Conversion to logical from NaN is not "
                              "possible.")
        out = a != 0
        return bool(out) if out.ndim == 0 else _normalise(out)

    def f_cast(self, x, name):
        name = str(name)
        if name == "logical":
            return self.f_logical(x)
        if name not in nt.INTS and name not in ("single", "double"):
            raise MatlabError(f"Invalid data type '{name}'.")
        return getattr(self, f"f_{name}")(x)

    # ── limits ──────────────────────────────────────────────────

    @staticmethod
    def _class_of(arg, default: str) -> str:
        if arg is None:
            return default
        if isinstance(arg, str):
            return str(arg)
        return nt.num_class(arg) or "double"

    def f_intmax(self, name=None):
        name = self._class_of(name, "int32")
        if name not in nt.INTS:
            raise MatlabError(f"Invalid class name '{name}': intmax takes "
                              f"an integer class.")
        return nt.INTS[name].type(nt.intlimits(name)[1])

    def f_intmin(self, name=None):
        name = self._class_of(name, "int32")
        if name not in nt.INTS:
            raise MatlabError(f"Invalid class name '{name}': intmin takes "
                              f"an integer class.")
        return nt.INTS[name].type(nt.intlimits(name)[0])

    def f_flintmax(self, name=None):
        name = self._class_of(name, "double")
        if name == "single":
            return np.float32(2 ** 24)
        return float(2 ** 53)

    def f_realmax(self, name=None):
        name = self._class_of(name, "double")
        if name == "single":
            return np.float32(np.finfo(np.float32).max)
        return float(np.finfo(float).max)

    def f_realmin(self, name=None):
        name = self._class_of(name, "double")
        if name == "single":
            return np.float32(np.finfo(np.float32).tiny)
        return float(np.finfo(float).tiny)

    # ── tests ───────────────────────────────────────────────────

    def f_isinteger(self, x):
        return nt.is_int(x)

    def f_isfloat(self, x):
        return self.f_class(x) in ("double", "single")

    def f_isstring(self, x):
        return isinstance(x, (Str, StrArray))

    # ── integer arithmetic ──────────────────────────────────────

    def f_idivide(self, a, b, option="fix"):
        cls = nt.check_pair(a, b)
        if cls not in nt.INTS:
            raise MatlabError("At least one input to idivide must be an "
                              "integer class.")
        rounding = {"fix": np.trunc, "floor": np.floor, "ceil": np.ceil,
                    "round": lambda v: np.sign(v) * np.floor(np.abs(v)
                                                              + 0.5)}
        if str(option) not in rounding:
            raise MatlabError("idivide: the rounding is 'fix', 'floor', "
                              "'ceil' or 'round'.")
        with np.errstate(divide="ignore", invalid="ignore"):
            q = rounding[str(option)](nt.to_double(_as_array(a)) /
                                      nt.to_double(_as_array(b)))
        return _normalise(np.asarray(nt.cast(q, cls)))

    def _bitwise(self, op, a, b):
        cls = nt.check_pair(a, b)
        x, cx = _bits(a)
        y, cy = _bits(b)
        if cls in nt.INTS:
            x, y = nt.cast(x, cls), nt.cast(y, cls)
        out = op(np.asarray(x), np.asarray(y))
        if cls in nt.INTS:
            return _normalise(np.asarray(out).astype(nt.INTS[cls]))
        return _normalise(np.asarray(out).astype(float))

    def f_bitand(self, a, b):
        return self._bitwise(np.bitwise_and, a, b)

    def f_bitor(self, a, b):
        return self._bitwise(np.bitwise_or, a, b)

    def f_bitxor(self, a, b):
        return self._bitwise(np.bitwise_xor, a, b)

    def f_bitshift(self, a, n):
        cls = nt.num_class(a)
        x, _ = _bits(a)
        k = np.asarray(n).astype(int)
        with np.errstate(over="ignore"):
            out = np.where(k >= 0, np.left_shift(x, np.abs(k).astype(x.dtype)),
                           np.right_shift(x, np.abs(k).astype(x.dtype)))
        if cls in nt.INTS:
            return _normalise(np.asarray(out).astype(nt.INTS[cls]))
        return _normalise(np.asarray(out & np.uint64(2 ** 53 - 1))
                          .astype(float))

    def f_bitcmp(self, a):
        cls = nt.num_class(a)
        if cls in nt.INTS:
            return _normalise(np.asarray(np.invert(np.asarray(a))))
        x, _ = _bits(a)
        return _normalise((np.uint64(2 ** 53 - 1) - x).astype(float))

    # ── strings ─────────────────────────────────────────────────

    def f_string(self, *args):
        """``string(x)``: text, numbers or a cell of text as string(s)."""
        if len(args) != 1:
            raise MatlabError("string takes one input.")
        x = args[0]
        if isinstance(x, StrArray):
            return x
        if isinstance(x, str):
            return Str(x)
        if isinstance(x, Cell):
            if not all(isinstance(v, str) or np.isscalar(v) for v in x):
                raise MatlabError("Conversion to string from cell is not "
                                  "possible unless every element is text "
                                  "or a number.")
            return _strarray([v if isinstance(v, str) else _text(v)
                              for v in x], x.rows)
        if isinstance(x, (bool, np.bool_)):
            return Str("true" if x else "false")
        arr = np.asarray(x)
        if arr.dtype == object or arr.ndim > 2:
            raise MatlabError("Conversion to string is not possible for "
                              "this value.")
        flat = [_text(v) for v in arr.reshape(-1, order="F")]
        return _strarray(flat, arr.shape[0] if arr.ndim == 2 else 1)

    def f_strlength(self, s):
        """``strlength(s)``: the number of characters of each string."""
        if isinstance(s, StrArray) or isinstance(s, Cell):
            lengths = [self._len(v) for v in s]
            return _normalise(np.array(lengths, dtype=float))
        return self._len(s)

    @staticmethod
    def _len(v):
        if not isinstance(v, str):
            raise MatlabError("strlength: the input must be text.")
        return len(v)


def _text(v) -> str:
    """A number as ``string`` writes it: up to 15 significant digits."""
    v = v.item() if isinstance(v, np.generic) else v
    if isinstance(v, str):
        return v
    if isinstance(v, (bool, int)):
        return str(int(v))
    if isinstance(v, float):
        if v != v:
            return "NaN"
        if v in (float("inf"), float("-inf")):
            return "Inf" if v > 0 else "-Inf"
        return f"{v:.15g}"
    return _number(v)
