"""
Dates and durations.
====================
``datetime``, ``duration`` and the calendar durations (``calmonths``…) that
go with them, plus the functions that make and take them apart.

A :class:`Datetime` holds a 2-D numpy ``datetime64[us]`` array (``NaT`` is
the missing value); a :class:`Duration` holds a 2-D float array of seconds.
Both are immutable values: ``t(2) = x`` and ``t.Format = …`` copy first.
They define Python's operators, so ``+``, ``-``, ``<`` and ``==`` in MATLAB
code reach them through the runtime's ordinary arithmetic; they set
``__array_ufunc__ = None`` so that ``[1 2 3] + hours(1)`` is theirs to answer.

Tables keep a datetime or duration as one variable (a column), so both
classes also provide ``take(idx)`` and ``texts()`` as a table column must.

Not in Evans: time zones, leap seconds, locales (month names are English),
the ``'datetime'`` display of a scalar on its own two lines.
"""

from __future__ import annotations

import datetime as _dt
import math
import re

import numpy as np

from . import matlab_runtime as _mr  # noqa: F401
from .matlab_runtime import (
    COLON,
    Cell,
    MatlabError,
    _as2d,
    _as_array,
    _nargout,
    _normalise,
)

_MONTHS = ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"]
_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
         "Sunday"]
_TOKEN = re.compile(r"'[^']*'|y+|u+|M+|d+|E+|H+|h+|m+|s+|S+|a|.")
_US = np.timedelta64(1, "us")
_NAT = np.datetime64("NaT", "us")


# ──────────────────────────────────────────────────────────────
#  Formats
# ──────────────────────────────────────────────────────────────

def format_one(t: _dt.datetime, fmt: str) -> str:
    """One moment in a MATLAB datetime format (``'dd-MMM-uuuu HH:mm:ss'``)."""
    out = []
    for tok in _TOKEN.findall(fmt):
        c = tok[0]
        n = len(tok)
        if c == "'":
            out.append(tok[1:-1] if len(tok) > 2 else "'")
        elif c in "yu":
            out.append(f"{t.year % 100:02d}" if n == 2 else f"{t.year:04d}")
        elif c == "M":
            out.append(_MONTHS[t.month - 1] if n >= 4 else
                       _MONTHS[t.month - 1][:3] if n == 3 else
                       f"{t.month:02d}" if n == 2 else str(t.month))
        elif c == "d":
            out.append(f"{t.day:02d}" if n >= 2 else str(t.day))
        elif c == "E":
            name = _DAYS[t.weekday()]
            out.append(name if n >= 4 else name[:3])
        elif c == "H":
            out.append(f"{t.hour:02d}" if n >= 2 else str(t.hour))
        elif c == "h":
            h = t.hour % 12 or 12
            out.append(f"{h:02d}" if n >= 2 else str(h))
        elif c == "m":
            out.append(f"{t.minute:02d}" if n >= 2 else str(t.minute))
        elif c == "s":
            out.append(f"{t.second:02d}" if n >= 2 else str(t.second))
        elif c == "S":
            out.append(f"{t.microsecond:06d}"[:n])
        elif c == "a":
            out.append("AM" if t.hour < 12 else "PM")
        else:
            out.append(tok)
    return "".join(out)


def _regex_for(fmt: str):
    """A MATLAB input format → (compiled regex, list of field names)."""
    parts, fields = [], []
    for tok in _TOKEN.findall(fmt):
        c, n = tok[0], len(tok)
        if c == "'":
            parts.append(re.escape(tok[1:-1]))
        elif c in "yu":
            parts.append(r"(\d{2})" if n == 2 else r"(\d{4})")
            fields.append("yy" if n == 2 else "y")
        elif c == "M":
            parts.append(r"([A-Za-z]+)" if n >= 3 else r"(\d{1,2})")
            fields.append("Mname" if n >= 3 else "M")
        elif c == "d":
            parts.append(r"(\d{1,2})")
            fields.append("d")
        elif c == "E":
            parts.append(r"[A-Za-z]+")
        elif c in "Hh":
            parts.append(r"(\d{1,2})")
            fields.append("H" if c == "H" else "h")
        elif c == "m":
            parts.append(r"(\d{1,2})")
            fields.append("m")
        elif c == "s":
            parts.append(r"(\d{1,2})")
            fields.append("s")
        elif c == "S":
            parts.append(r"(\d+)")
            fields.append("S")
        elif c == "a":
            parts.append(r"(AM|PM|am|pm)")
            fields.append("a")
        else:
            parts.append(re.escape(tok))
    return re.compile("^" + "".join(parts) + "$"), fields


_DEFAULT_PARSE = ["yyyy-MM-dd HH:mm:ss", "yyyy-MM-dd'T'HH:mm:ss",
                  "yyyy-MM-dd HH:mm", "yyyy-MM-dd", "dd-MMM-yyyy HH:mm:ss",
                  "dd-MMM-yyyy", "yyyy/MM/dd HH:mm:ss", "yyyy/MM/dd",
                  "MM/dd/yyyy HH:mm:ss", "MM/dd/yyyy", "HH:mm:ss"]


def parse_one(text: str, fmt: str | None):
    """Text → a ``datetime64[us]`` (or None when it does not match)."""
    for f in ([fmt] if fmt else _DEFAULT_PARSE):
        rx, fields = _regex_for(f)
        m = rx.match(text.strip())
        if not m:
            continue
        v = dict(y=_dt.date.today().year, M=1, d=1, H=0, m=0, s=0, S="0",
                 a=None)
        try:
            for name, g in zip(fields, m.groups()):
                if name == "Mname":
                    low = g.lower()
                    hit = [i for i, mn in enumerate(_MONTHS)
                           if mn.lower() == low or mn[:3].lower() == low[:3]]
                    if not hit:
                        raise ValueError
                    v["M"] = hit[0] + 1
                elif name == "yy":
                    v["y"] = 2000 + int(g) if int(g) < 50 else 1900 + int(g)
                elif name in ("S", "a"):
                    v[name] = g
                elif name == "h":
                    v["H"] = int(g)
                else:
                    v[name] = int(g)
            if v["a"]:
                pm = v["a"].upper() == "PM"
                v["H"] = v["H"] % 12 + (12 if pm else 0)
            micro = int((v["S"] + "000000")[:6])
            return np.datetime64(_dt.datetime(
                v["y"], v["M"], v["d"], v["H"], v["m"], v["s"], micro), "us")
        except ValueError:
            continue
    return None


# ──────────────────────────────────────────────────────────────
#  Shared behaviour
# ──────────────────────────────────────────────────────────────

def _bool_result(a: np.ndarray):
    return _normalise(np.asarray(a, dtype=bool))


def _numbers(x, what: str) -> np.ndarray:
    """A numeric operand as a 2-D float array."""
    if isinstance(x, (str, Cell)) or x is None:
        raise MatlabError(f"Operand to {what} must be numeric.")
    return _as2d(_as_array(x)).astype(float)


class _Vec:
    """What datetime and duration have in common: a 2-D array and indexing."""

    __array_ufunc__ = None
    __hash__ = None
    ml_vec = True
    ml_class = ""

    def __init__(self, a: np.ndarray, fmt: str | None = None) -> None:
        self.a = a
        self.fmt = fmt

    def _new(self, a, fmt="same"):
        return type(self)(a, self.fmt if fmt == "same" else fmt)

    def __len__(self) -> int:
        return int(self.a.size)

    def ml_shape(self):
        return self.a.shape

    def flat(self) -> np.ndarray:
        return self.a.reshape(-1, order="F")

    def take(self, idx):
        return self._new(self.flat()[np.asarray(idx, dtype=int)]
                         .reshape(-1, 1))

    @classmethod
    def blank(cls, n: int, fmt=None):
        return cls(np.full((n, 1), cls._missing()), fmt)

    # x(i), x(i, j)
    def __call__(self, *args, **_):
        if not args:
            return self
        pos = _mr.Runtime._indices
        if len(args) == 1:
            if args[0] is None or args[0] is COLON:
                return self._new(self.flat().reshape(-1, 1))
            idx = np.atleast_1d(pos(None, args[0], self.a.size))
            out = self.flat()[idx]
            row = self.a.shape[0] == 1 and self.a.shape[1] > 1
            return self._new(out.reshape(1, -1) if row else
                             out.reshape(-1, 1))
        rows = np.atleast_1d(pos(None, args[0], self.a.shape[0]))
        cols = np.atleast_1d(pos(None, args[1], self.a.shape[1]))
        return self._new(self.a[np.ix_(rows, cols)])

    def _ml_assign(self, rt, kind, key, rest, value, owned=False):
        if kind == "." and key == "Format" and not rest:
            if not isinstance(value, str):
                raise MatlabError("Format must be a character vector.")
            return self._new(self.a, self._check_format(value))
        if kind != "()" or rest:
            raise MatlabError(f"Cannot assign into a {self.ml_class} that "
                              f"way.")
        flat = self.flat().copy()
        if isinstance(value, np.ndarray) and value.size == 0:
            idx = np.atleast_1d(rt._indices(key[-1], flat.size))
            keep = np.delete(flat, idx)
            row = self.a.shape[0] == 1
            return self._new(keep.reshape(1, -1) if row else
                             keep.reshape(-1, 1))
        other = self._coerce_value(value)
        a = key[-1]
        k = (rt._grow_index(a, flat.size) if not (a is COLON or (
            isinstance(a, np.ndarray) and a.size != 1)) else None)
        if k is not None:
            if k >= flat.size:
                pad = np.full(k + 1 - flat.size, self._missing())
                flat = np.concatenate([flat, pad])
            idx = np.array([k])
        else:
            idx = np.atleast_1d(rt._indices(a, flat.size))
        flat[idx] = other.flat()
        row = self.a.shape[0] == 1
        return self._new(flat.reshape(1, -1) if row else flat.reshape(-1, 1))

    # display ----------------------------------------------------
    def __repr__(self) -> str:
        r, c = self.a.shape
        texts = self.texts2d()
        if r * c == 1:
            return texts[0][0]
        if r * c == 0:
            return f"{r}×{c} empty {self.ml_class} array"
        width = max(len(t) for row in texts for t in row)
        lines = ["   " + "   ".join(t.rjust(width) for t in row)
                 for row in texts]
        return f"{r}×{c} {self.ml_class} array\n\n" + "\n".join(lines)

    def texts(self) -> list[str]:
        return [self._text(v) for v in self.flat()]

    def texts2d(self) -> list[list[str]]:
        return [[self._text(v) for v in row] for row in self.a]


# ──────────────────────────────────────────────────────────────
#  datetime
# ──────────────────────────────────────────────────────────────

_AUTO = None


class Datetime(_Vec):
    ml_class = "datetime"

    @staticmethod
    def _missing():
        return _NAT

    @staticmethod
    def _check_format(fmt: str) -> str:
        return fmt

    def _coerce_value(self, value):
        if isinstance(value, Datetime):
            return value
        if isinstance(value, (str, Cell)):
            return make_datetime_from_text(value, None)
        raise MatlabError("Only a datetime can be assigned into a datetime "
                          "array.")

    def _format(self) -> str:
        if self.fmt:
            return self.fmt
        f = self.flat()
        ok = f[~np.isnat(f)]
        if ok.size and np.any(ok != ok.astype("datetime64[D]")
                              .astype("datetime64[us]")):
            return "dd-MMM-uuuu HH:mm:ss"
        return "dd-MMM-uuuu"

    def _text(self, v) -> str:
        if np.isnat(v):
            return "NaT"
        return format_one(v.astype("datetime64[us]").astype(_dt.datetime),
                          self._format())

    # components
    def parts(self):
        a = self.a
        months = a.astype("datetime64[M]")
        days = a.astype("datetime64[D]")
        y = a.astype("datetime64[Y]").astype(int) + 1970
        mo = months.astype(int) % 12 + 1
        d = (days - months.astype("datetime64[D]")).astype(int) + 1
        tod = (a - days.astype("datetime64[us]")).astype(
            "timedelta64[us]").astype(float) / 1e6
        nat = np.isnat(a)
        out = []
        for v in (y, mo, d, np.floor(tod / 3600), np.floor(tod / 60) % 60,
                  tod % 60):
            v = v.astype(float)
            v[nat] = np.nan
            out.append(v)
        return out

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        names = ("Year", "Month", "Day", "Hour", "Minute", "Second")
        if name in names:
            return _num(self.parts()[names.index(name)])
        if name == "Format":
            return self._format()
        if name == "TimeZone":
            return ""
        raise AttributeError(f"Unrecognized property '{name}' for class "
                             f"'datetime'.")

    def datenum(self) -> np.ndarray:
        days = (self.a.astype("datetime64[us]") - np.datetime64(
            "1970-01-01T00:00:00", "us")).astype("timedelta64[us]").astype(
            float) / 86400e6
        days = days + 719529.0
        days[np.isnat(self.a)] = np.nan
        return days

    # arithmetic -------------------------------------------------
    def _shift(self, secs: np.ndarray, sign: float = 1.0):
        s = secs * sign
        us = np.where(np.isnan(s), 0, np.round(s * 1e6)).astype(np.int64)
        out = self.a + us.astype("timedelta64[us]")
        out = np.where(np.isnan(s), _NAT, out)
        return Datetime(out, self.fmt)

    def __add__(self, other):
        if isinstance(other, Datetime):
            raise MatlabError("Binary operator '+' is not defined for "
                              "'datetime' and 'datetime' operands.")
        if isinstance(other, CalDuration):
            return other.apply(self, 1)
        if isinstance(other, Duration):
            return self._shift(other.a)
        return self._shift(_numbers(other, "datetime +") * 86400.0)

    __radd__ = __add__

    def __sub__(self, other):
        if isinstance(other, Datetime):
            d = (self.a - other.a).astype("timedelta64[us]").astype(
                float) / 1e6
            d = np.where(np.isnat(self.a) | np.isnat(other.a), np.nan, d)
            return Duration(d)
        if isinstance(other, CalDuration):
            return other.apply(self, -1)
        if isinstance(other, Duration):
            return self._shift(other.a, -1.0)
        return self._shift(_numbers(other, "datetime -") * 86400.0, -1.0)

    def __rsub__(self, other):
        raise MatlabError("Binary operator '-' is not defined for the "
                          "operands: only a datetime can be subtracted "
                          "from a datetime.")

    def _cmp(self, other, op):
        if isinstance(other, (str, Cell)):
            other = make_datetime_from_text(other, None)
        if not isinstance(other, Datetime):
            raise MatlabError("Comparison is only defined between "
                              "datetimes (or text read as one).")
        res = op(self.a, other.a)
        return _bool_result(res)

    def __eq__(self, o):
        return self._cmp(o, lambda x, y: x == y)

    def __ne__(self, o):
        return self._cmp(o, lambda x, y: (x != y) & ~np.isnat(x) &
                         ~np.isnat(y) | np.isnat(x) ^ np.isnat(y))

    def __lt__(self, o):
        return self._cmp(o, lambda x, y: x < y)

    def __le__(self, o):
        return self._cmp(o, lambda x, y: x <= y)

    def __gt__(self, o):
        return self._cmp(o, lambda x, y: x > y)

    def __ge__(self, o):
        return self._cmp(o, lambda x, y: x >= y)

    # builtins that dispatch here --------------------------------
    def _sorted_flat(self, descend=False):
        f = self.flat()
        key = np.where(np.isnat(f), np.iinfo(np.int64).max,
                       f.astype("datetime64[us]").astype(np.int64))
        order = np.argsort(key, kind="stable")
        if descend:
            nat = np.isnat(f)
            order = np.concatenate([np.nonzero(nat)[0],
                                    order[~nat[order]][::-1]])
        return order

    def keys(self) -> np.ndarray:
        f = self.flat()
        return np.where(np.isnat(f), np.iinfo(np.int64).min,
                        f.astype("datetime64[us]").astype(np.int64))

    def ml_sort(self, lib, mode="ascend", nargout=1):
        order = self._sorted_flat(str(mode).lower() == "descend")
        out = self._new(self.flat()[order].reshape(self.a.shape
                        if self.a.shape[0] == 1 else (-1, 1)))
        return (out, _num((order + 1.0).reshape(out.a.shape))) \
            if nargout > 1 else out

    def ml_unique(self, lib, *_, nargout=1):
        f = self.flat()
        f = f[~np.isnat(f)]
        u = np.unique(f)
        return self._new(u.reshape(-1, 1))

    def ml_min(self, lib, *a, nargout=1):
        return self._extreme(np.min)

    def ml_max(self, lib, *a, nargout=1):
        return self._extreme(np.max)

    def _extreme(self, fn):
        f = self.flat()
        f = f[~np.isnat(f)]
        return self._new(fn(f).reshape(1, 1)) if f.size else \
            self._new(np.array([[_NAT]]))

    def ml_mean(self, lib, *a):
        f = self.flat()
        f = f[~np.isnat(f)]
        ints = f.astype("datetime64[us]").astype(np.int64)
        return self._new(np.array([[np.int64(round(ints.mean()))]])
                         .astype("datetime64[us]")) if f.size else \
            self._new(np.array([[_NAT]]))

    ml_median = ml_mean

    def ml_diff(self, lib, n=1):
        f = self
        for _ in range(int(n)):
            v = f.flat()
            f = Duration(((v[1:] - v[:-1]).astype("timedelta64[us]")
                          .astype(float) / 1e6).reshape(-1, 1)) \
                if f is self else Duration(np.diff(f.flat()).reshape(-1, 1))
        return f

    def ml_isequal(self, lib, *others):
        return all(isinstance(o, Datetime) and o.a.shape == self.a.shape
                   and bool(np.all((o.a == self.a)
                                   | (np.isnat(o.a) & np.isnat(self.a))))
                   for o in others)

    def ml_isnan(self, lib):
        return _bool_result(np.isnat(self.a))

    ml_isnat = ml_isnan

    def ml_datenum(self, lib, *a):
        return _num(self.datenum())

    def ml_datestr(self, lib, *rest):
        return lib.f_datestr(_num(self.datenum()), *rest)

    def ml_char(self, lib, *a):
        t = self.texts()
        return t[0] if len(t) == 1 else Cell(t, rows=len(t))

    ml_string = ml_cellstr = ml_char

    def ml_posixtime(self, lib):
        return _num((self.datenum() - 719529.0) * 86400.0)


def _num(a: np.ndarray):
    """A 2-D float array → the runtime's usual number shape."""
    return _normalise(np.asarray(a))


def make_datetime_from_text(text, fmt):
    items = [text] if isinstance(text, str) else list(text)
    out = []
    for s in items:
        if not isinstance(s, str):
            raise MatlabError("datetime: text input must be char vectors.")
        v = parse_one(s, fmt)
        if v is None:
            if s.strip().lower() in ("nat", ""):
                v = _NAT
            else:
                raise MatlabError(
                    f"Unable to convert the text '{s}' to datetime. Specify "
                    f"the format with 'InputFormat'." if not fmt else
                    f"Unable to read '{s}' as a datetime using the format "
                    f"'{fmt}'.")
        out.append(v)
    arr = np.array(out, dtype="datetime64[us]")
    col = isinstance(text, Cell) and text.dims[1] == 1 and len(items) > 1
    return Datetime(arr.reshape(-1, 1) if col else arr.reshape(1, -1))


def from_components(parts: list[np.ndarray]) -> np.ndarray:
    """y, m, d[, h, mi, s] (broadcast; months and days may overflow)."""
    parts = list(np.broadcast_arrays(*[np.asarray(p, dtype=float)
                                       for p in parts]))
    while len(parts) < 6:
        parts.append(np.zeros_like(parts[0]))
    y, mo, d, h, mi, s = parts
    nan = np.isnan(y + mo + d + h + mi + s)
    months = ((np.nan_to_num(y) - 1970) * 12 + np.nan_to_num(mo) - 1)
    months = np.floor(months).astype(np.int64)
    base = months.astype("datetime64[M]").astype("datetime64[D]").astype(
        "datetime64[us]")
    us = (np.nan_to_num(d - 1) * 86400e6 + np.nan_to_num(h) * 3600e6
          + np.nan_to_num(mi) * 60e6 + np.nan_to_num(s) * 1e6)
    out = base + np.round(us).astype(np.int64).astype("timedelta64[us]")
    return np.where(nan, _NAT, out)


# ──────────────────────────────────────────────────────────────
#  duration
# ──────────────────────────────────────────────────────────────

_UNITS = {"y": ("yr", 365.2425 * 86400), "d": ("day", 86400.0),
          "h": ("hr", 3600.0), "m": ("min", 60.0), "s": ("sec", 1.0)}


class Duration(_Vec):
    ml_class = "duration"

    @staticmethod
    def _missing():
        return np.nan

    @staticmethod
    def _check_format(fmt: str) -> str:
        if fmt in _UNITS or re.fullmatch(
                r"(d{1,2}:)?(h{1,2})(:m{1,2})?(:s{1,2})?(\.S+)?|"
                r"m{1,2}:s{1,2}(\.S+)?", fmt):
            return fmt
        raise MatlabError(f"'{fmt}' is not a valid duration format. Use "
                          f"'s', 'm', 'h', 'd', 'y', 'hh:mm:ss', "
                          f"'dd:hh:mm:ss', 'mm:ss' or 'hh:mm'.")

    def _coerce_value(self, value):
        if isinstance(value, Duration):
            return value
        raise MatlabError("Only a duration can be assigned into a duration "
                          "array.")

    def _text(self, v) -> str:
        fmt = self.fmt or "hh:mm:ss"
        if np.isnan(v):
            return "NaN"
        if np.isinf(v):
            return "Inf" if v > 0 else "-Inf"
        if fmt in _UNITS:
            name, k = _UNITS[fmt]
            x = v / k
            word = name + ("s" if name == "day" and abs(x) != 1 else "")
            return f"{x:.5g} {word}"
        frac = re.search(r"\.(S+)", fmt)
        digits = len(frac.group(1)) if frac else 0
        sign = "-" if v < 0 else ""
        total = round(abs(v), digits) + 1e-9
        if "d:" in fmt:
            d, rest = divmod(total, 86400)
            parts = [f"{int(d)}"]
        else:
            rest, parts = total, []
        want_h = "h" in fmt
        h, rest = divmod(rest, 3600) if want_h else (0, rest)
        if want_h:
            parts.append(f"{int(h):02d}")
        m, s = divmod(rest, 60)
        if ":m" in fmt or fmt.startswith("m"):
            parts.append(f"{int(m):02d}")
        if "s" in fmt:
            parts.append(f"{int(s):02d}" if not digits else
                         f"{int(s):02d}." + f"{s - int(s):.{digits}f}"[2:])
        out = ":".join(parts)
        return sign + out

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        if name == "Format":
            return self.fmt or "hh:mm:ss"
        raise AttributeError(f"Unrecognized property '{name}' for class "
                             f"'duration'.")

    def as_unit(self, unit: str) -> np.ndarray:
        return self.a / _UNITS[unit][1]

    # arithmetic -------------------------------------------------
    def _other(self, o, what):
        if isinstance(o, Duration):
            return o.a
        if isinstance(o, (Datetime, CalDuration, str, Cell)):
            return None
        return _numbers(o, what) * 86400.0

    def __add__(self, o):
        if isinstance(o, Datetime):
            return o.__add__(self)
        a = self._other(o, "duration +")
        if a is None:
            raise MatlabError("Binary operator '+' is not defined for "
                              "these operands.")
        return Duration(self.a + a, self.fmt)

    __radd__ = __add__

    def __sub__(self, o):
        a = self._other(o, "duration -")
        if a is None:
            raise MatlabError("Binary operator '-' is not defined for "
                              "these operands.")
        return Duration(self.a - a, self.fmt)

    def __rsub__(self, o):
        a = self._other(o, "duration -")
        if a is None:
            raise MatlabError("Binary operator '-' is not defined for "
                              "these operands.")
        return Duration(a - self.a, self.fmt)

    def __neg__(self):
        return Duration(-self.a, self.fmt)

    def __abs__(self):
        return Duration(np.abs(self.a), self.fmt)

    def __mul__(self, o):
        if isinstance(o, (Duration, Datetime)):
            raise MatlabError("Binary operator '*' is not defined for two "
                              "durations.")
        return Duration(self.a * _numbers(o, "duration *"), self.fmt)

    __rmul__ = __mul__

    def __truediv__(self, o):
        if isinstance(o, Duration):
            with np.errstate(divide="ignore", invalid="ignore"):
                return _num(self.a / o.a)
        with np.errstate(divide="ignore", invalid="ignore"):
            return Duration(self.a / _numbers(o, "duration /"), self.fmt)

    def __rtruediv__(self, o):
        raise MatlabError("A number cannot be divided by a duration.")

    def _cmp(self, other, op):
        if isinstance(other, Duration):
            b = other.a
        elif isinstance(other, (Datetime, str, Cell)):
            raise MatlabError("A duration compares only with durations "
                              "and numbers (days).")
        else:
            b = _numbers(other, "duration comparison") * 86400.0
        return _bool_result(op(self.a, b))

    def __eq__(self, o):
        return self._cmp(o, lambda x, y: x == y)

    def __ne__(self, o):
        return self._cmp(o, lambda x, y: x != y)

    def __lt__(self, o):
        return self._cmp(o, lambda x, y: x < y)

    def __le__(self, o):
        return self._cmp(o, lambda x, y: x <= y)

    def __gt__(self, o):
        return self._cmp(o, lambda x, y: x > y)

    def __ge__(self, o):
        return self._cmp(o, lambda x, y: x >= y)

    def keys(self) -> np.ndarray:
        return self.flat()

    # builtins ---------------------------------------------------
    def ml_sort(self, lib, mode="ascend", nargout=1):
        f = self.flat()
        order = np.argsort(f, kind="stable")
        if str(mode).lower() == "descend":
            nat = np.isnan(f)
            order = np.concatenate([np.nonzero(nat)[0],
                                    order[~nat[order]][::-1]])
        out = self._new(f[order].reshape(self.a.shape
                        if self.a.shape[0] == 1 else (-1, 1)))
        return (out, _num((order + 1.0).reshape(out.a.shape))) \
            if nargout > 1 else out

    def ml_unique(self, lib, *_, nargout=1):
        f = self.flat()
        return self._new(np.unique(f[~np.isnan(f)]).reshape(-1, 1))

    def _red(self, fn):
        f = self.flat()
        f = f[~np.isnan(f)]
        return self._new(np.array([[fn(f) if f.size else np.nan]]))

    def ml_min(self, lib, *a, nargout=1):
        return self._red(np.min)

    def ml_max(self, lib, *a, nargout=1):
        return self._red(np.max)

    def ml_sum(self, lib, *a):
        return self._red(np.sum)

    def ml_mean(self, lib, *a):
        return self._red(np.mean)

    def ml_median(self, lib, *a):
        return self._red(np.median)

    def ml_abs(self, lib):
        return abs(self)

    def ml_diff(self, lib, n=1):
        return self._new(np.diff(self.flat(), n=int(n)).reshape(-1, 1))

    def ml_isequal(self, lib, *others):
        return all(isinstance(o, Duration) and o.a.shape == self.a.shape
                   and bool(np.all(o.a == self.a)) for o in others)

    def ml_isnan(self, lib):
        return _bool_result(np.isnan(self.a))

    def ml_char(self, lib, *a):
        t = self.texts()
        return t[0] if len(t) == 1 else Cell(t, rows=len(t))

    ml_string = ml_cellstr = ml_char


# ──────────────────────────────────────────────────────────────
#  calendar durations
# ──────────────────────────────────────────────────────────────

class CalDuration:
    """Months, days and a time of day, added to a datetime by the calendar."""

    __array_ufunc__ = None
    __hash__ = None
    ml_class = "calendarDuration"

    def __init__(self, months, days, secs) -> None:
        self.m = np.asarray(months, dtype=float)
        self.d = np.asarray(days, dtype=float)
        self.s = np.asarray(secs, dtype=float)

    def ml_shape(self):
        return np.broadcast(self.m, self.d, self.s).shape

    def __len__(self):
        return int(np.prod(self.ml_shape()))

    def apply(self, t: Datetime, sign: int) -> Datetime:
        m = np.broadcast_to(self.m * sign, np.broadcast(self.m, t.a).shape)
        y, mo, d, *_ = t.parts()
        total = (y * 12 + (mo - 1) + m)
        yy = np.floor(total / 12)
        mm = total - yy * 12 + 1
        first = from_components([yy, mm, np.ones_like(yy)])
        nxt = from_components([yy, mm + 1, np.ones_like(yy)])
        dim = ((nxt - first).astype("timedelta64[D]").astype(float))
        dd = np.minimum(d, dim)
        tod = t.a - t.a.astype("datetime64[D]").astype("datetime64[us]")
        out = from_components([yy, mm, dd]) + tod
        out = np.where(np.isnan(m), _NAT, out)
        res = Datetime(out, t.fmt)
        shift = self.d * sign * 86400.0 + self.s * sign
        return res._shift(np.broadcast_to(shift, out.shape).astype(float))

    def __add__(self, o):
        if isinstance(o, Datetime):
            return self.apply(o, 1)
        if isinstance(o, CalDuration):
            return CalDuration(self.m + o.m, self.d + o.d, self.s + o.s)
        raise MatlabError("A calendar duration adds only to a datetime or "
                          "another calendar duration.")

    __radd__ = __add__

    def __sub__(self, o):
        if isinstance(o, CalDuration):
            return CalDuration(self.m - o.m, self.d - o.d, self.s - o.s)
        raise MatlabError("Binary operator '-' is not defined for these "
                          "operands.")

    def __neg__(self):
        return CalDuration(-self.m, -self.d, -self.s)

    def __mul__(self, k):
        k = _numbers(k, "calendar duration *")
        return CalDuration(self.m * k, self.d * k, self.s * k)

    __rmul__ = __mul__

    def __repr__(self) -> str:
        parts = []
        sh = self.ml_shape()
        n = int(np.prod(sh))
        m, d, s = (np.broadcast_to(x, sh).reshape(-1)
                   for x in (self.m, self.d, self.s))
        for k in range(n):
            bits = []
            if m[k]:
                y, mo = divmod(int(m[k]), 12) if m[k] > 0 else \
                    (-(int(-m[k]) // 12), -(int(-m[k]) % 12))
                if y:
                    bits.append(f"{y}y")
                if mo:
                    bits.append(f"{mo}mo")
            if d[k]:
                bits.append(f"{d[k]:g}d")
            if s[k] or not bits:
                t = abs(s[k])
                bits.append(("-" if s[k] < 0 else "") +
                            f"{int(t // 3600):02d}:{int(t % 3600 // 60):02d}"
                            f":{int(t % 60):02d}")
            parts.append(" ".join(bits))
        return parts[0] if n == 1 else "   ".join(parts)


# ──────────────────────────────────────────────────────────────
#  The functions
# ──────────────────────────────────────────────────────────────

def _unit_fn(unit: str, per_second: float):
    def fn(self, x=None, *more):
        if isinstance(x, Duration):
            return _num(x.a / per_second)
        if x is None:
            x = 1.0
        a = _numbers(x, f"{unit}")
        return Duration(a * per_second, unit)
    return fn


def _civil(self, name):
    def fn(t):
        if not isinstance(t, Datetime):
            raise MatlabError(f"{name} needs a datetime.")
        idx = ("Year", "Month", "Day", "Hour", "Minute", "Second").index(
            name)
        return _num(t.parts()[idx])
    return fn


def _need_dt(t, fn):
    if not isinstance(t, Datetime):
        raise MatlabError(f"{fn} needs a datetime.")
    return t


class DateLibrary:
    """Mixed into the runtime's function library."""

    # ── construction ───────────────────────────────────────────

    def f_datetime(self, *args):
        pos, opts = [], {}
        k = 0
        names = ("format", "inputformat", "convertfrom", "timezone",
                 "locale", "pivotyear")
        while k < len(args):
            a = args[k]
            if isinstance(a, str) and a.lower() in names and k + 1 < len(
                    args) and pos:
                opts[a.lower()] = args[k + 1]
                k += 2
                continue
            pos.append(a)
            k += 1
        if opts.get("timezone"):
            raise MatlabError("datetime: time zones are not supported in "
                              "Evans.")
        fmt = opts.get("format")
        out = None
        if not pos:
            out = Datetime(np.array([[np.datetime64(_dt.datetime.now(),
                                                    "us")]]))
        elif "convertfrom" in opts:
            src = str(opts["convertfrom"]).lower()
            x = _numbers(pos[0], "datetime")
            if src == "datenum":
                days = x - 719529.0
            elif src == "posixtime":
                days = x / 86400.0
            elif src == "excel":
                days = x - 25569.0
            elif src == "juliandate":
                days = x - 2440587.5
            else:
                raise MatlabError(f"datetime: 'ConvertFrom' '{src}' is not "
                                  f"supported.")
            us = np.round(days * 86400e6)
            arr = np.where(np.isnan(us), _NAT,
                           np.nan_to_num(us).astype(np.int64).astype(
                               "timedelta64[us]") + np.datetime64(0, "us"))
            out = Datetime(arr)
        elif len(pos) == 1 and isinstance(pos[0], str) and pos[0].lower() in (
                "now", "today", "yesterday", "tomorrow"):
            now = np.datetime64(_dt.datetime.now(), "us")
            word = pos[0].lower()
            if word != "now":
                now = now.astype("datetime64[D]").astype("datetime64[us]")
                now = now + np.timedelta64({"today": 0, "yesterday": -1,
                                            "tomorrow": 1}[word], "D")
            out = Datetime(np.array([[now]]))
        elif len(pos) == 1 and isinstance(pos[0], (str, Cell)):
            out = make_datetime_from_text(pos[0], opts.get("inputformat"))
        elif len(pos) == 1 and isinstance(pos[0], Datetime):
            out = pos[0]
        elif len(pos) == 1 and isinstance(pos[0], np.ndarray) \
                and pos[0].ndim == 2 and pos[0].shape[1] in (3, 6):
            m = pos[0]
            out = Datetime(from_components(
                [m[:, j] for j in range(m.shape[1])]).reshape(-1, 1))
        elif 3 <= len(pos) <= 7:
            if len(pos) == 7:
                raise MatlabError("datetime: milliseconds as a seventh "
                                  "argument are not supported; use a "
                                  "fractional second.")
            arr = from_components([_numbers(p, "datetime") for p in pos])
            out = Datetime(arr)
        else:
            raise MatlabError("datetime needs year, month, day, "
                              "[hour, minute, second], or text.")
        if fmt:
            out.fmt = str(fmt)
        return out

    def f_NaT(self, *dims):
        n = int(dims[0]) if dims else 1
        m = int(dims[1]) if len(dims) > 1 else n
        return Datetime(np.full((n, m), _NAT))

    f_seconds = _unit_fn("s", 1.0)
    f_minutes = _unit_fn("m", 60.0)
    f_hours = _unit_fn("h", 3600.0)
    f_days = _unit_fn("d", 86400.0)
    f_years = _unit_fn("y", 365.2425 * 86400)

    def f_milliseconds(self, x):
        if isinstance(x, Duration):
            return _num(x.a * 1000.0)
        return Duration(_numbers(x, "milliseconds") / 1000.0, "s")

    def f_duration(self, *args):
        fmt = None
        pos = list(args)
        if len(pos) >= 2 and isinstance(pos[-2], str) and pos[-2].lower() \
                in ("format", "inputformat"):
            fmt = pos[-1]
            pos = pos[:-2]
        if len(pos) == 1 and isinstance(pos[0], (str, Cell)):
            items = [pos[0]] if isinstance(pos[0], str) else list(pos[0])
            secs = []
            for s in items:
                text = s.strip()
                sign = -1 if text.startswith("-") else 1
                bits = text.lstrip("-").split(":")
                try:
                    nums = [float(x) for x in bits]
                except ValueError:
                    nums = []
                if not 2 <= len(nums) <= 4:
                    raise MatlabError(f"duration: cannot read '{s}'. Use "
                                      f"'hh:mm:ss'.")
                if len(nums) == 2:
                    nums.append(0.0)
                if len(nums) == 3:
                    nums.insert(0, 0.0)
                d, h, mi, sc = nums
                secs.append(sign * (d * 86400 + h * 3600 + mi * 60 + sc))
            out = Duration(np.array(secs, dtype=float).reshape(-1, 1)
                           if len(secs) > 1 else np.array([[secs[0]]]))
        else:
            parts = [_numbers(p, "duration") for p in pos]
            if len(parts) == 1:
                parts = parts * 1
            while len(parts) < 3:
                parts.append(np.zeros_like(parts[0]))
            h, mi, s = np.broadcast_arrays(*parts[:3])
            tot = h * 3600 + mi * 60 + s
            if len(parts) > 3:
                tot = tot + parts[3] / 1000.0
            out = Duration(tot)
        if fmt:
            out.fmt = Duration._check_format(str(fmt))
        return out

    def f_caldays(self, x=0):
        a = _numbers(x, "caldays")
        return CalDuration(0 * a, a, 0 * a)

    def f_calweeks(self, x=0):
        a = _numbers(x, "calweeks")
        return CalDuration(0 * a, 7 * a, 0 * a)

    def f_calmonths(self, x=0):
        a = _numbers(x, "calmonths")
        return CalDuration(a, 0 * a, 0 * a)

    def f_calquarters(self, x=0):
        a = _numbers(x, "calquarters")
        return CalDuration(3 * a, 0 * a, 0 * a)

    def f_calyears(self, x=0):
        a = _numbers(x, "calyears")
        return CalDuration(12 * a, 0 * a, 0 * a)

    # ── questions ──────────────────────────────────────────────

    def f_isdatetime(self, x):
        return isinstance(x, Datetime)

    def f_isduration(self, x):
        return isinstance(x, Duration)

    def f_iscalendarduration(self, x):
        return isinstance(x, CalDuration)

    def f_isnat(self, x):
        _need_dt(x, "isnat")
        return _bool_result(np.isnat(x.a))

    # ── components ─────────────────────────────────────────────

    def f_year(self, t):
        return _civil(self, "Year")(t)

    def f_month(self, t):
        return _civil(self, "Month")(t)

    def f_day(self, t):
        return _civil(self, "Day")(t)

    def f_hour(self, t):
        return _civil(self, "Hour")(t)

    def f_minute(self, t):
        return _civil(self, "Minute")(t)

    def f_second(self, t):
        return _civil(self, "Second")(t)

    @_nargout
    def f_ymd(self, t, nargout=1):
        p = _need_dt(t, "ymd").parts()
        return tuple(_num(x) for x in p[:3])

    @_nargout
    def f_hms(self, t, nargout=1):
        if isinstance(t, Duration):
            s = t.a
            h = np.fix(s / 3600)
            return (_num(h), _num(np.fix((s - h * 3600) / 60)),
                    _num(np.mod(np.abs(s), 60)))
        p = _need_dt(t, "hms").parts()
        return tuple(_num(x) for x in p[3:])

    @_nargout
    def f_weekday(self, t, form=None, nargout=1):
        _need_dt(t, "weekday")
        days = t.a.astype("datetime64[D]").astype(int)
        num = ((days + 4) % 7 + 1).astype(float)      # 1970-01-01: Thursday
        num[np.isnat(t.a)] = np.nan
        long_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday",
                      "Friday", "Saturday"]
        short = str(form or "short").lower() != "long"
        names = [("" if np.isnan(n) else (long_names[int(n) - 1][:3] if short
                  else long_names[int(n) - 1])) for n in num.reshape(-1)]
        if nargout >= 2:
            return _num(num), (names[0] if len(names) == 1 else
                               Cell(names, rows=len(names)))
        return _num(num)

    def f_timeofday(self, t):
        _need_dt(t, "timeofday")
        tod = (t.a - t.a.astype("datetime64[D]").astype("datetime64[us]")
               ).astype("timedelta64[us]").astype(float) / 1e6
        return Duration(np.where(np.isnat(t.a), np.nan, tod))

    def f_posixtime(self, t):
        return _need_dt(t, "posixtime").ml_posixtime(self)

    # ── calendar arithmetic ────────────────────────────────────

    def f_between(self, t1, t2, *_):
        _need_dt(t1, "between")
        _need_dt(t2, "between")
        shape = np.broadcast(t1.a, t2.a).shape
        a = np.broadcast_to(t1.a, shape)
        b = np.broadcast_to(t2.a, shape)
        months = np.zeros(shape)
        days = np.zeros(shape)
        secs = np.zeros(shape)
        for idx in np.ndindex(shape):
            x, y = a[idx], b[idx]
            if np.isnat(x) or np.isnat(y):
                months[idx] = days[idx] = secs[idx] = np.nan
                continue
            sgn = 1 if y >= x else -1
            lo, hi = (x, y) if sgn == 1 else (y, x)
            ya, ma, da, *_ = Datetime(np.array([[lo]])).parts()
            yb, mb, db, *_ = Datetime(np.array([[hi]])).parts()
            n = int((yb[0, 0] - ya[0, 0]) * 12 + mb[0, 0] - ma[0, 0])
            while n > 0 and CalDuration(n, 0, 0).apply(
                    Datetime(np.array([[lo]])), 1).a[0, 0] > hi:
                n -= 1
            mid = CalDuration(n, 0, 0).apply(Datetime(np.array([[lo]])),
                                             1).a[0, 0]
            rest = float((hi - mid) / _US) / 1e6
            nd = math.floor(rest / 86400)
            months[idx] = sgn * n
            days[idx] = sgn * nd
            secs[idx] = sgn * (rest - nd * 86400)
        return CalDuration(months, days, secs)

    def f_dateshift(self, t, how, unit=None, *_):
        _need_dt(t, "dateshift")
        how = str(how).lower()
        unit = str(unit).lower() if unit is not None else ""
        if how not in ("start", "end"):
            raise MatlabError("dateshift: the second argument must be "
                              "'start' or 'end'.")
        a = t.a
        step = {"year": "Y", "month": "M", "day": "D", "hour": "h",
                "minute": "m", "second": "s"}
        if unit == "quarter":
            y, mo, *_ = t.parts()
            first = from_components([y, (np.floor((mo - 1) / 3) * 3) + 1,
                                     np.ones_like(y)])
            start = first
            nxt = from_components([y, (np.floor((mo - 1) / 3) * 3) + 4,
                                   np.ones_like(y)])
        elif unit == "week":
            days = a.astype("datetime64[D]")
            dow = (days.astype(int) + 3) % 7      # Monday = 0
            start = (days - dow.astype("timedelta64[D]")).astype(
                "datetime64[us]")
            nxt = start + np.timedelta64(7, "D")
        elif unit in step:
            start = a.astype(f"datetime64[{step[unit]}]").astype(
                "datetime64[us]")
            nxt = (a.astype(f"datetime64[{step[unit]}]") + 1).astype(
                "datetime64[us]")
        else:
            raise MatlabError(f"dateshift: unit '{unit}' is not supported; "
                              f"use year, quarter, month, week, day, hour, "
                              f"minute or second.")
        out = start if how == "start" else nxt - _US
        return Datetime(np.where(np.isnat(a), _NAT, out), t.fmt)

    def f_isbetween(self, t, lo, hi, *_):
        return _bool_result(_between(t, lo, hi))

    def f_addtodate(self, d, q, unit):
        t = Datetime(Datetime(_nums_to_dt(d)).a)
        unit = str(unit).lower()
        if unit in ("year", "month"):
            c = CalDuration(_numbers(q, "addtodate") * (12 if unit == "year"
                                                        else 1), 0, 0)
        else:
            mult = {"day": 86400, "hour": 3600, "minute": 60, "second": 1,
                    "week": 7 * 86400, "millisecond": 1e-3}[unit]
            c = CalDuration(0, 0, _numbers(q, "addtodate") * mult)
        return _num(c.apply(t, 1).ml_datenum(self))


def _nums_to_dt(d):
    x = _numbers(d, "datetime")
    return from_components([np.full_like(x, 1970), np.ones_like(x),
                            np.ones_like(x)]) + np.round(
        (x - 719529.0) * 86400e6).astype(np.int64).astype("timedelta64[us]")


def _between(t, lo, hi):
    r = t >= lo
    s = t <= hi
    return np.asarray(r, dtype=bool) & np.asarray(s, dtype=bool)


# Names of builtins that a datetime, duration or table answers for itself
# (the object has an ``ml_<name>`` method); see :func:`install_dispatch`.
DISPATCHED = ("sort", "unique", "min", "max", "sum", "mean", "median", "abs",
              "diff", "isequal", "isnan", "datenum", "datestr", "char",
              "string", "cellstr", "join")

__all__ = ["Datetime", "Duration", "CalDuration", "DateLibrary",
           "format_one", "parse_one", "from_components"]
