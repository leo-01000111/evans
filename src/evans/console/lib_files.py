"""
MATLAB file I/O.
================
Delimited text, ``fopen`` and friends, JSON.

A mixin of :class:`.matlab_runtime._Library`: each ``f_<name>`` method is
the MATLAB function ``<name>``. It is imported by :mod:`.matlab_runtime`
just before ``_Library`` is defined, so the helpers above that line can be
imported from it by name; anything defined further down is reached through
the module (``_mr._sprintf``) at call time. Import :mod:`.matlab_runtime` first, never this module on
its own: the two import each other.

Tables
------
:class:`ColumnTable` is what ``readtable``, ``table`` and ``array2table``
return: one numpy column (or list of text) per variable. It subclasses the
display-only :class:`.matlab_runtime.Table`, so ``size`` already knows it.
``T(rows, vars)`` reaches it through ``Runtime.call`` (a table is callable);
``T.Name`` through ``Runtime.field`` (an attribute).

Files
-----
Open files live in a dict on the runtime (``rt._fids``), numbered from 3;
1 and 2 are the console. They are Python binary files: text mode (``'wt'``)
only changes ``\\n`` to ``\\r\\n`` on Windows, as MATLAB's does.
"""

from __future__ import annotations

import csv
import json
import math
import os
import re
import sys

import numpy as np

from . import matlab_runtime as _mr  # noqa: F401
from .matlab_runtime import (
    TABLE_WIDTH,
    Cell,
    MatlabError,
    Struct,
    StructArray,
    Table,
    _as2d,
    _as_array,
    _as_text,
    _is_number,
    _named,
    _nargout,
    _normalise,
    _scalar,
    _shape,
)

# ──────────────────────────────────────────────────────────────
#  Small helpers
# ──────────────────────────────────────────────────────────────

_REAL = r"(?:(?:\d+\.?\d*|\.\d+)(?:[eEdD][+-]?\d+)?|[Ii]nf(?:inity)?|NaN|nan)"
_REAL_RE = re.compile(rf"[+-]?{_REAL}")
_COMPLEX_RE = re.compile(rf"([+-]?{_REAL})?([+-]{_REAL}?)[ij]")
_SPREADSHEET = (".xls", ".xlsx", ".xlsm", ".xlsb", ".ods", ".xltx", ".xltm")
_TEXT_EXT = (".csv", ".txt", ".dat", ".tsv", ".text", "")
_DELIMS = {"comma": ",", ",": ",", "tab": "\t", "\\t": "\t", "\t": "\t",
           "space": " ", " ": " ", "semi": ";", ";": ";", "bar": "|",
           "|": "|"}


def _real(text: str) -> float:
    t = text.replace("d", "e").replace("D", "e")
    low = t.lower().lstrip("+-")
    if low in ("inf", "infinity"):
        return -math.inf if t.startswith("-") else math.inf
    if low == "nan":
        return math.nan
    return float(t)


def _number(field: str):
    """A text field as a number, or ``None`` if it is not one."""
    s = field.strip()
    if not s:
        return None
    if _REAL_RE.fullmatch(s):
        return _real(s)
    m = _COMPLEX_RE.fullmatch(s)
    if m:
        re_part = _real(m.group(1)) if m.group(1) else 0.0
        im = m.group(2)
        im_part = _real(im + "1" if im in "+-" else im)
        return complex(re_part, im_part)
    return None


def _opt_name(x) -> str:
    if not isinstance(x, str):
        raise MatlabError("Expected a name-value pair: an option name, then "
                          "its value.")
    return x.lower()


def _options(args, allowed: dict[str, str], fn: str) -> dict:
    """``'Name', value`` pairs → {canonical name: value}, case-insensitive."""
    if len(args) % 2:
        raise MatlabError(f"{fn}: options must come in name-value pairs.")
    out = {}
    for name, value in zip(args[0::2], args[1::2]):
        key = _opt_name(name)
        if key not in allowed:
            raise MatlabError(f"{fn}: the '{name}' option is not supported "
                              f"in Evans.")
        out[allowed[key]] = value
    return out


def _truth(x) -> bool:
    if isinstance(x, str):
        if x.lower() in ("true", "on"):
            return True
        if x.lower() in ("false", "off"):
            return False
        raise MatlabError(f"Expected true or false, got '{x}'.")
    return bool(np.all(np.asarray(x)))


def _delimiter(value, fn: str) -> str:
    if isinstance(value, Cell) and len(value) == 1:
        value = value[0]
    if not isinstance(value, str) or not value:
        raise MatlabError(f"{fn}: 'Delimiter' must be a character vector "
                          f"such as ',' or '\\t'.")
    return _DELIMS.get(value.lower(), _mr._escapes(value))


def _int_arg(x, what: str) -> int:
    v = float(np.asarray(x).reshape(-1)[0]) if np.size(x) else math.nan
    if not math.isfinite(v) or v != int(v) or v < 0:
        raise MatlabError(f"{what} must be a nonnegative integer.")
    return int(v)


def _ext(path: str) -> str:
    return os.path.splitext(path)[1].lower()


def _read_text(path: str, shown) -> str:
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        raise MatlabError(
            f"Unable to find or open '{_as_text(shown)}'. Check the path and "
            f"filename or file permissions.",
            "MATLAB:textio:textio:FileNotFound") from None
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


def _refuse_spreadsheet(path: str, fn: str) -> None:
    if _ext(path) in _SPREADSHEET:
        raise MatlabError(f"{fn}: spreadsheet files ({_ext(path)}) need "
                          f"openpyxl, which Evans doesn't ship. Save the "
                          f"sheet as .csv and read that.")


def _detect(lines: list[str]) -> str | None:
    """The delimiter most lines use: ',', tab, ';' — else whitespace."""
    best, score = None, 0
    for d in (",", "\t", ";"):
        n = sum(1 for ln in lines if d in ln)
        if n > score:
            best, score = d, n
    return best


def _split(line: str, delim: str | None) -> list[str]:
    if delim is None or delim == " ":
        return line.split()
    if len(delim) == 1:
        return [f.strip() for f in next(csv.reader(
            [line], delimiter=delim, skipinitialspace=True))]
    return [f.strip() for f in line.split(delim)]


def _g15(v) -> str:
    """MATLAB's long g: up to 15 significant digits, ``5`` not ``5.0``."""
    if isinstance(v, (bool, np.bool_)):
        return "1" if v else "0"
    if isinstance(v, (complex, np.complexfloating)):
        im = v.imag
        return f"{_g15(v.real)}{'+' if im >= 0 or math.isnan(im) else '-'}" \
               f"{_g15(abs(im))}i"
    v = float(v)
    if math.isnan(v):
        return "NaN"
    if math.isinf(v):
        return "Inf" if v > 0 else "-Inf"
    if v == 0:
        return "0"
    return f"{v:.15g}"


def _column_letters(s: str) -> int:
    n = 0
    for ch in s.upper():
        n = n * 26 + ord(ch) - 64
    return n


_CELL_REF = re.compile(r"([A-Za-z]+)(\d+)")


def _spreadsheet_range(text: str):
    """'B2:D5' or 'B2..D5' → (r1, c1, r2, c2), 1-based; r2/c2 None if open."""
    parts = re.split(r":|\.\.", text.strip())
    refs = [_CELL_REF.fullmatch(p.strip()) for p in parts]
    if not 1 <= len(parts) <= 2 or not all(refs):
        raise MatlabError(f"'{text}' is not a range Evans understands; use "
                          f"the form 'A1:C5' or a start cell 'B2'.")
    r1, c1 = int(refs[0].group(2)), _column_letters(refs[0].group(1))
    if len(refs) == 1:
        return r1, c1, None, None
    return r1, c1, int(refs[1].group(2)), _column_letters(refs[1].group(1))


def make_valid_name(name: str) -> str:
    """``matlab.lang.makeValidName``."""
    if re.fullmatch(r"[A-Za-z]\w{0,62}", name) and not keyword_matlab(name):
        return name
    out, cap = [], False
    for ch in name.strip():
        if ch.isspace():
            cap = True
            continue
        out.append(ch.upper() if cap and ch.islower() else ch)
        cap = False
    s = re.sub(r"[^A-Za-z0-9_]", "_", "".join(out))
    if keyword_matlab(s):
        s = "x" + s[:1].upper() + s[1:]
    if not s or not s[0].isalpha():
        s = "x" + s
    return s[:63]


_MATLAB_KEYWORDS = {
    "break", "case", "catch", "classdef", "continue", "else", "elseif",
    "end", "for", "function", "global", "if", "otherwise", "parfor",
    "persistent", "return", "spmd", "switch", "try", "while"}


def keyword_matlab(s: str) -> bool:
    return s in _MATLAB_KEYWORDS


def _unique(names: list[str]) -> list[str]:
    """``matlab.lang.makeUniqueStrings``: a repeat becomes ``a_1``, ``a_2``."""
    seen, out = set(), []
    for n in names:
        if n in seen:
            k = 1
            while f"{n}_{k}" in seen or f"{n}_{k}" in names:
                k += 1
            n = f"{n}_{k}"
        seen.add(n)
        out.append(n)
    return out


def _column_major(a) -> list:
    return [_scalar(v) for v in _as2d(_as_array(a)).reshape(-1, order="F")]


def _shape_output(values: list, size_arg, char: bool = False):
    """fscanf / fread's ``sizeA``: column, ``n`` elements, or ``[m n]``."""
    if size_arg is None:
        m = None
    else:
        s = np.asarray(size_arg, float).reshape(-1)
        m = int(s[0]) if s.size == 2 else None
    if m is None:
        a = np.asarray(values, dtype=float).reshape(-1, 1)
        return a if a.size != 1 else _scalar(a[0, 0])
    if m <= 0:
        return np.zeros((0, 0))
    cols = -(-len(values) // m)
    a = np.zeros(m * cols)
    a[:len(values)] = values
    return _normalise(a.reshape((m, cols), order="F"))


def _limit(size_arg) -> float:
    if size_arg is None:
        return math.inf
    s = np.asarray(size_arg, float).reshape(-1)
    if s.size == 1:
        return s[0]
    if s.size == 2:
        return s[0] * s[1]
    raise MatlabError("sizeA must be a scalar or a two-element vector "
                      "[m n].")


# ──────────────────────────────────────────────────────────────
#  Tables
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
        return {n: (c[i].item() if isinstance(c, np.ndarray) else c[i])
                for n, c in zip(self.table.columns, self.table._data)}

    def __iter__(self):
        return (self[i] for i in range(len(self)))


def _positions(arg, n: int) -> list[int]:
    """A MATLAB subscript as 0-based positions; a call's ``:`` is None."""
    arg = _mr.COLON if arg is None else arg
    return np.atleast_1d(_mr.Runtime._indices(None, arg, n)).tolist()


class ColumnTable(Table):
    """
    A MATLAB table: named variables of equal height, one column each.
    A numeric variable is a 1-D numpy array (double or logical); a text
    variable is a list of char vectors.
    """

    def __init__(self, names, data, descriptions=None, height=None) -> None:
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

    @property
    def rows(self):
        return _Rows(self)

    @property
    def height(self) -> int:
        return self._height

    # T.Name and T.Properties
    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        if name == "Properties":
            return Struct(
                Description="",
                VariableNames=Cell(self.columns, rows=1),
                VariableDescriptions=Cell(self._descriptions, rows=1),
                RowNames=Cell())
        cols = self.__dict__.get("columns", [])
        if name in cols:
            return self.variable(cols.index(name))
        raise AttributeError(f"Unrecognized table variable name '{name}'.")

    def variable(self, k: int):
        col = self._data[k]
        if isinstance(col, np.ndarray):
            return _normalise(col.reshape(-1, 1))
        return Cell(col, rows=len(col))

    def is_text(self, k: int) -> bool:
        return not isinstance(self._data[k], np.ndarray)

    def _var_indices(self, arg) -> list[int]:
        if arg is None:
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

    # T(rows, vars)
    def __call__(self, *args, **_):
        if len(args) == 1:
            raise MatlabError("Subscripting into a table using one subscript "
                              "(as in t(i)) is not supported. Specify a row "
                              "subscript and a variable subscript, as in "
                              "t(rows,vars).")
        if len(args) != 2:
            raise MatlabError("Tables are two-dimensional: index as "
                              "t(rows, vars).")
        rows = _positions(args[0], self.height)
        ks = self._var_indices(args[1])
        data = []
        for k in ks:
            col = self._data[k]
            data.append(col[rows] if isinstance(col, np.ndarray)
                        else [col[i] for i in rows])
        desc = ([self._descriptions[k] for k in ks]
                if self._descriptions else [])
        return ColumnTable([self.columns[k] for k in ks], data, desc,
                           height=len(rows))

    def __repr__(self) -> str:
        n, w = self.height, len(self.columns)
        if n == 0 or w == 0:
            return f"{n}×{w} empty table"
        cells, widths, right = [], [], []
        for k, name in enumerate(self.columns):
            col = self._data[k]
            if not isinstance(col, np.ndarray):
                texts = ["{" + _mr._brief(v) + "}" if isinstance(v, str)
                         and v else "{0×0 char}" if v == "" else
                         _mr._brief(v) for v in col]
                right.append(False)
            elif col.dtype == bool:
                texts = ["true" if v else "false" for v in col]
                right.append(False)
            else:
                texts = [_short_g(v) for v in col]
                right.append(True)
            cells.append(texts)
            widths.append(max(len(name), *(len(t) for t in texts)))
        blocks, current, used = [], [], 0
        for k, wd in enumerate(widths):
            if current and used + wd + 4 > TABLE_WIDTH:
                blocks.append(current)
                current, used = [], 0
            current.append(k)
            used += wd + 4
        blocks.append(current)
        out = [f"{n}×{w} table", ""]
        for b, block in enumerate(blocks):
            if b:
                out.append("")
            out.append("    " + "    ".join(
                self.columns[k].center(widths[k]) for k in block).rstrip())
            out.append("    " + "    ".join("_" * widths[k] for k in block))
            out.append("")
            for i in range(n):
                out.append("    " + "    ".join(
                    cells[k][i].rjust(widths[k]) if right[k]
                    else cells[k][i].ljust(widths[k])
                    for k in block).rstrip())
        return "\n".join(out)


def _short_g(v) -> str:
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


def _as_column(value, k: int):
    """A ``table(...)`` argument → one variable's column."""
    if isinstance(value, Cell):
        r, c = value.dims
        if c != 1 and len(value):
            if r == 1 and c >= 1:
                raise MatlabError(
                    f"Argument {k} is a 1×{c} cell; a table variable must "
                    f"be a column, such as {{'a'; 'b'}}.")
        return list(value)
    if isinstance(value, str):
        raise MatlabError("A char vector as a table variable is not "
                          "supported in Evans; put the text in a cell, such "
                          "as {'abc'}.")
    if isinstance(value, (Struct, StructArray, Table)) or callable(value):
        raise MatlabError(f"Evans's tables hold numbers, logicals and text; "
                          f"argument {k} is none of these.")
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
                f"Argument {k} is a {a.shape[0]}×{a.shape[1]} matrix; Evans's "
                f"tables hold one column per variable. Use array2table to "
                f"split a matrix into variables.")
        a = a.reshape(-1)
    if a.dtype == bool:
        return a.copy()
    if np.iscomplexobj(a):
        return a.astype(complex)
    return a.astype(float)


# ──────────────────────────────────────────────────────────────
#  Delimited text: reading
# ──────────────────────────────────────────────────────────────

def _numeric_grid(rows: list[list[str]], empty: float):
    """Fields → (matrix, is_complex). Non-numbers become ``empty``."""
    width = max((len(r) for r in rows), default=0)
    values, cplx = [], False
    for r in rows:
        line = []
        for f in r:
            v = _number(f)
            if v is None:
                v = empty
            cplx |= isinstance(v, complex)
            line.append(v)
        line += [empty] * (width - len(r))
        values.append(line)
    if not values or width == 0:
        return np.zeros((0, 0))
    return np.array(values, dtype=complex if cplx else float)


def _result(a: np.ndarray):
    if a.size == 0:
        return np.zeros((0, 0))
    return _normalise(a)


def _apply_range(rows: list[list[str]], rng):
    """Cut a grid of fields to a range: text 'B2:C5' or [r1 c1 (r2 c2)]."""
    if isinstance(rng, str):
        r1, c1, r2, c2 = _spreadsheet_range(rng)
    else:
        v = [int(x) for x in np.asarray(rng, float).reshape(-1)]
        if len(v) == 2:
            r1, c1, r2, c2 = v[0], v[1], None, None
        elif len(v) == 4:
            r1, c1, r2, c2 = v
        else:
            raise MatlabError("'Range' must be 'A1:C5', a start cell 'B2', "
                              "[row col] or [r1 c1 r2 c2].")
    out = rows[r1 - 1:r2]
    return [r[c1 - 1:c2] for r in out]


def _parse_lines(text: str):
    lines = text.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    return lines


# ──────────────────────────────────────────────────────────────
#  fscanf / textscan scanning
# ──────────────────────────────────────────────────────────────

_SCAN_SPEC = re.compile(
    r"%(?P<skip>\*)?(?P<width>\d+)?(?:\.(?P<prec>\d+))?"
    r"(?P<size>l|h|8|16|32|64)?"
    r"(?P<conv>\[\^?\]?[^\]]*\]|[diouxXfeEgGscnq%]|f32|f64|d8|d16|d32|d64|"
    r"u8|u16|u32|u64)")
_INT_RE = re.compile(r"[+-]?\d+")
_FLOAT_RE = re.compile(
    r"[+-]?(?:(?:\d+\.?\d*|\.\d+)(?:[eEdD][+-]?\d+)?|[Ii]nf(?:inity)?|NaN)")


def _scan_format(fmt: str, fn: str) -> list[tuple]:
    """A scan format → [('ws',), ('lit', text), ('conv', match)]."""
    fmt = _mr._escapes(fmt)
    items, pos = [], 0
    while pos < len(fmt):
        ch = fmt[pos]
        if ch.isspace():
            while pos < len(fmt) and fmt[pos].isspace():
                pos += 1
            items.append(("ws",))
            continue
        if ch == "%":
            m = _SCAN_SPEC.match(fmt, pos)
            if not m:
                raise MatlabError(f"{fn}: the format '{fmt[pos:pos + 4]}' is "
                                  f"not one Evans understands.")
            if m.group("conv") == "%":
                items.append(("lit", "%"))
            else:
                items.append(("conv", m))
            pos = m.end()
            continue
        start = pos
        while pos < len(fmt) and fmt[pos] != "%" and not fmt[pos].isspace():
            pos += 1
        items.append(("lit", fmt[start:pos]))
    return items


def _skip_ws(text: str, pos: int, chars=" \t\r\n\f\v\b") -> int:
    while pos < len(text) and text[pos] in chars:
        pos += 1
    return pos


def _fscanf(text: str, fmt: str, limit: float):
    """Scan ``text``: (values, chars_only, count, characters consumed)."""
    items = _scan_format(fmt, "fscanf")
    convs = [it[1].group("conv") for it in items
             if it[0] == "conv" and not it[1].group("skip")]
    chars_only = bool(convs) and all(c in ("s", "c") or c.startswith("[")
                                     for c in convs)
    values: list = []
    count, pos = 0, 0
    if not any(k == "conv" for k, *_ in items):
        return values, False, 0, 0
    while count < limit:
        start = pos
        stop = False
        for item in items:
            if item[0] == "ws":
                pos = _skip_ws(text, pos)
                continue
            if item[0] == "lit":
                if text.startswith(item[1], pos):
                    pos += len(item[1])
                    continue
                stop = True
                break
            m = item[1]
            conv = m.group("conv")
            width = int(m.group("width")) if m.group("width") else None
            if conv != "c" and not conv.startswith("["):
                pos = _skip_ws(text, pos)
            if pos >= len(text):
                stop = True
                break
            window = text[pos:pos + width] if width else text[pos:]
            got = None
            if conv in "dium":
                mm = _INT_RE.match(window)
                got = mm and [float(mm.group())]
            elif conv == "o":
                mm = re.match(r"[0-7]+", window)
                got = mm and [float(int(mm.group(), 8))]
            elif conv in "xX":
                mm = re.match(r"(?:0[xX])?[0-9a-fA-F]+", window)
                got = mm and [float(int(mm.group(), 16))]
            elif conv in "feEgGn" or conv.startswith("f"):
                mm = _FLOAT_RE.match(window)
                got = mm and [_real(mm.group())]
            elif conv == "s":
                mm = re.match(r"\S+", window)
                got = mm and [float(ord(c)) for c in mm.group()]
            elif conv == "c":
                n = width or 1
                mm = re.match(rf"[\s\S]{{1,{n}}}", text[pos:])
                got = mm and [float(ord(c)) for c in mm.group()]
            elif conv.startswith("["):
                mm = re.match(conv + "+", window)
                got = mm and [float(ord(c)) for c in mm.group()]
            else:
                raise MatlabError(f"fscanf: '%{conv}' is not supported in "
                                  f"Evans.")
            if not mm:
                stop = True
                break
            pos += len(mm.group())
            if not m.group("skip"):
                room = int(min(limit - count, len(got)))
                values.extend(got[:room])
                count += room
                if count >= limit:
                    break
        if stop or pos == start:
            break
    return values, chars_only, count, pos


# ──────────────────────────────────────────────────────────────
#  JSON
# ──────────────────────────────────────────────────────────────

def _from_json(v):
    """A parsed JSON value → MATLAB, as jsondecode maps it."""
    if v is None:
        return np.zeros((0, 0))
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return _scalar(float(v))
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        names = _unique([make_valid_name(k) if k else "x" for k in v])
        return Struct({n: _from_json(x) for n, x in zip(names, v.values())})
    # an array
    if not v:
        return np.zeros((0, 0))
    if all(isinstance(x, bool) for x in v):
        return np.array(v, dtype=bool).reshape(-1, 1) if len(v) > 1 else v[0]
    numeric = [x for x in v if x is not None]
    if numeric and all(isinstance(x, (int, float)) and not isinstance(x, bool)
                       for x in numeric):
        a = np.array([math.nan if x is None else float(x) for x in v])
        return a.reshape(-1, 1) if a.size > 1 else _scalar(a[0])
    if all(isinstance(x, list) for x in v):
        inner = [_from_json(x) for x in v]
        vector = [_is_number(x) or (isinstance(x, np.ndarray) and x.ndim == 2
                                    and x.shape[1] == 1) for x in inner]
        if all(vector) and len({np.size(x) for x in inner}) == 1:
            kinds = {np.asarray(x).dtype == bool for x in inner}
            if len(kinds) == 1:
                m = np.vstack([np.asarray(x).reshape(1, -1) for x in inner])
                return m if kinds == {True} else m.astype(float)
        if all(isinstance(x, np.ndarray) and x.ndim == 2 and x.shape[1] > 1
               for x in inner) and len({x.shape for x in inner}) == 1:
            raise MatlabError("jsondecode: this JSON is an N-D array; Evans "
                              "supports 2-D arrays only.")
        return Cell(inner, rows=len(inner))
    if all(isinstance(x, dict) for x in v):
        structs = [_from_json(x) for x in v]
        keys = [list(s) for s in structs]
        if all(k == keys[0] for k in keys):
            return (StructArray(structs, rows=len(structs))
                    if len(structs) > 1 else structs[0])
        return Cell(structs, rows=len(structs))
    items = [_from_json(x) for x in v]
    return Cell(items, rows=len(items))


def _to_json(x, nan_null: bool):
    """A MATLAB value → a Python value that :func:`json.dumps` writes."""
    def num(v):
        if isinstance(v, (bool, np.bool_)):
            return bool(v)
        if isinstance(v, (complex, np.complexfloating)):
            raise MatlabError("jsonencode: complex numbers have no JSON form.")
        v = float(v)
        if not math.isfinite(v):
            return None if nan_null else v
        return int(v) if v.is_integer() and abs(v) < 1e15 else v

    if isinstance(x, str):
        return x
    if x is None:
        return []
    if isinstance(x, ColumnTable):
        return [{n: _to_json(row[n], nan_null) for n in x.columns}
                for row in x.rows]
    if isinstance(x, StructArray):
        r, c = x.dims
        if r > 1 and c > 1:
            raise MatlabError("jsonencode: Evans encodes struct arrays that "
                              "are vectors only.")
        items = [_to_json(s, nan_null) for s in x]
        return items[0] if len(items) == 1 else items
    if isinstance(x, dict):
        return {str(k): _to_json(v, nan_null) for k, v in x.items()}
    if isinstance(x, Cell):
        r, c = x.dims
        if r > 1 and c > 1:
            raise MatlabError("jsonencode: Evans encodes cell arrays that are "
                              "vectors only; a matrix cell has no single "
                              "JSON layout.")
        return [_to_json(v, nan_null) for v in x]
    if _is_number(x):
        return num(x)
    if isinstance(x, np.ndarray):
        if x.size == 0:
            return []
        if x.dtype == object:
            raise MatlabError("jsonencode: this value has no JSON form.")
        if x.size == 1:
            return num(x.reshape(-1)[0])
        if x.ndim == 1 or (x.ndim == 2 and 1 in x.shape):
            return [num(v) for v in x.reshape(-1)]
        return [[num(v) for v in row] for row in x]
    raise MatlabError(f"jsonencode: a {type(x).__name__} has no JSON form.")


# ──────────────────────────────────────────────────────────────
#  Binary precisions
# ──────────────────────────────────────────────────────────────

_PRECISION = {
    "uint8": "u1", "uchar": "u1", "unsigned char": "u1", "char": "u1",
    "char*1": "u1", "int8": "i1", "schar": "i1", "signed char": "i1",
    "integer*1": "i1", "uint16": "u2", "ushort": "u2", "int16": "i2",
    "short": "i2", "integer*2": "i2", "uint32": "u4", "uint": "u4",
    "ulong": "u4", "int32": "i4", "int": "i4", "long": "i4",
    "integer*4": "i4", "uint64": "u8", "int64": "i8", "integer*8": "i8",
    "single": "f4", "float32": "f4", "float": "f4", "real*4": "f4",
    "double": "f8", "float64": "f8", "real*8": "f8"}
_MACHINE = {"n": "=", "native": "=", "l": "<", "ieee-le": "<", "b": ">",
            "ieee-be": ">", "a": "<", "s": ">", "ieee-le.l64": "<",
            "ieee-be.l64": ">"}


def _precision(text: str, fn: str):
    """'int16', '*char', 'uint8=>char' → (dtype code, output is char)."""
    p = text.strip().lower()
    out = None
    if p.startswith("*"):
        p = p[1:]
        out = p
    elif "=>" in p:
        p, out = (s.strip() for s in p.split("=>", 1))
    if p not in _PRECISION:
        raise MatlabError(f"{fn}: the precision '{text}' is not supported in "
                          f"Evans.")
    if out not in (None, "double", "char"):
        raise MatlabError(
            f"{fn}: Evans keeps the numbers it reads as double; use "
            f"'{p}' (or '{p}=>double') rather than '{text}'.")
    return _PRECISION[p], out == "char"


def _machine(fmt) -> str:
    if fmt is None:
        return "="
    key = _as_text(fmt).lower()
    if key not in _MACHINE:
        raise MatlabError(f"The machine format '{key}' is not supported.")
    return _MACHINE[key]


class _OpenFile:
    def __init__(self, fh, name: str, permission: str, text: bool,
                 machine: str, encoding: str) -> None:
        self.fh = fh
        self.name = name
        self.permission = permission
        self.text = text
        self.machine = machine
        self.encoding = encoding

    def size(self) -> int:
        self.fh.flush()
        return os.fstat(self.fh.fileno()).st_size


_PERMISSIONS = {"r": "rb", "w": "wb", "a": "ab", "r+": "r+b", "w+": "w+b",
                "a+": "a+b", "A": "ab", "W": "wb"}
_INVALID_FID = ("Invalid file identifier. Use fopen to generate a valid file "
                "identifier.")


# ──────────────────────────────────────────────────────────────
#  The library
# ──────────────────────────────────────────────────────────────

class FileLibrary:
    """readmatrix, fopen, jsondecode and the rest."""

    # ── delimited numbers ──────────────────────────────────────

    def f_readmatrix(self, filename, *args):
        opts = _options(args, {"delimiter": "Delimiter",
                               "numheaderlines": "NumHeaderLines",
                               "range": "Range", "filetype": "FileType",
                               "outputtype": "OutputType"}, "readmatrix")
        path = self.rt.resolve(filename)
        _refuse_spreadsheet(path, "readmatrix")
        if str(opts.get("FileType", "text")).lower() not in ("text",
                                                             "delimitedtext"):
            raise MatlabError("readmatrix: Evans reads text files only.")
        if str(opts.get("OutputType", "double")).lower() != "double":
            raise MatlabError("readmatrix: Evans reads numbers as double "
                              "only ('OutputType', 'double').")
        lines = _parse_lines(_read_text(path, filename))
        delim = (_delimiter(opts["Delimiter"], "readmatrix")
                 if "Delimiter" in opts else _detect(lines))
        if "Range" in opts:
            rows = [_split(ln, delim) for ln in lines]
            rows = _apply_range(rows, opts["Range"])
        else:
            skip = (_int_arg(opts["NumHeaderLines"], "NumHeaderLines")
                    if "NumHeaderLines" in opts else None)
            body = lines[skip:] if skip is not None else lines
            rows = [_split(ln, delim) for ln in body if ln.strip()]
            if skip is None:
                # Leading lines with no number in them are a header.
                while rows and all(_number(f) is None for f in rows[0]):
                    rows.pop(0)
        return _result(_numeric_grid(rows, math.nan))

    def _dlm(self, fn: str, filename, delim, r=0, c=0, rng=None):
        path = self.rt.resolve(filename)
        _refuse_spreadsheet(path, fn)
        lines = [ln for ln in _parse_lines(_read_text(path, filename))
                 if ln.strip()]
        if delim is None or delim == "":
            delim = _detect(lines)
        else:
            delim = _delimiter(delim, fn)
        r2 = c2 = None
        if rng is not None:
            if isinstance(rng, str):
                r1, c1, r2, c2 = _spreadsheet_range(rng)
                r, c = r1 - 1, c1 - 1
                r2 = r2 - 1 if r2 is not None else None
                c2 = c2 - 1 if c2 is not None else None
            else:
                v = [int(x) for x in np.asarray(rng, float).reshape(-1)]
                if len(v) != 4:
                    raise MatlabError(f"{fn}: the range must be [R1 C1 R2 C2] "
                                      f"(0-based) or 'A1..B7'.")
                r, c, r2, c2 = v
        rows = [_split(ln, delim) for ln in lines]
        rows = rows[r:None if r2 is None else r2 + 1]
        width = max((len(x) for x in rows), default=0)
        if c2 is not None:
            width = c2 + 1
        out = []
        for i, fields in enumerate(rows):
            line = []
            for j in range(c, width):
                f = fields[j] if j < len(fields) else ""
                v = _number(f)
                if v is None:
                    if f.strip():
                        raise MatlabError(
                            f"Mismatch between file and format character "
                            f"vector.\nTrouble reading 'Numeric' field from "
                            f"file (row number {r + i + 1}, field number "
                            f"{j + 1}) ==> {f}")
                    v = 0.0
                line.append(v)
            out.append(line)
        if r2 is not None:
            while len(out) < r2 - r + 1:
                out.append([0.0] * max(width - c, 0))
        if not out or not out[0]:
            return np.zeros((0, 0))
        cplx = any(isinstance(v, complex) for ln in out for v in ln)
        return _result(np.array(out, dtype=complex if cplx else float))

    def f_dlmread(self, filename, delim=None, *args):
        if len(args) == 1:
            return self._dlm("dlmread", filename, delim, rng=args[0])
        if len(args) == 2:
            return self._dlm("dlmread", filename, delim,
                             _int_arg(args[0], "R"), _int_arg(args[1], "C"))
        if len(args) == 3:
            return self._dlm("dlmread", filename, delim,
                             _int_arg(args[0], "R"), _int_arg(args[1], "C"),
                             args[2])
        if args:
            raise MatlabError("Too many input arguments.")
        return self._dlm("dlmread", filename, delim)

    def f_csvread(self, filename, r=0, c=0, rng=None):
        return self._dlm("csvread", filename, ",", _int_arg(r, "R"),
                         _int_arg(c, "C"), rng)

    @_named
    def f_writematrix(self, A, *args, names=None):
        filename = None
        if args and len(args) % 2:
            filename, args = args[0], args[1:]
        opts = _options(args, {"delimiter": "Delimiter",
                               "writemode": "WriteMode",
                               "filetype": "FileType"}, "writematrix")
        if filename is None:
            name = names[0] if names and names[0] else None
            filename = f"{name}.txt" if name else "matrix.txt"
        path = self.rt.resolve(filename)
        _refuse_spreadsheet(path, "writematrix")
        ftype = str(opts.get("FileType", "text")).lower()
        if ftype == "spreadsheet":
            _refuse_spreadsheet(".xlsx", "writematrix")
        if ftype != "text":
            raise MatlabError(f"writematrix: unknown 'FileType' '{ftype}'.")
        if "FileType" not in opts and _ext(path) not in _TEXT_EXT:
            raise MatlabError(f"writematrix: '{_ext(path)}' is not a file "
                              f"extension Evans writes; use .csv, .txt or "
                              f".dat, or 'FileType', 'text'.")
        delim = _delimiter(opts.get("Delimiter", ","), "writematrix")
        mode = str(opts.get("WriteMode", "overwrite")).lower()
        if mode not in ("overwrite", "append"):
            raise MatlabError(f"writematrix: 'WriteMode' '{mode}' is not "
                              f"supported for text files.")
        if isinstance(A, str):
            raise MatlabError("writematrix of char is not supported in "
                              "Evans; use fprintf to write text.")
        if isinstance(A, (Cell, Struct, StructArray, Table)):
            raise MatlabError("writematrix writes numeric or logical "
                              "arrays; use writetable for a table.")
        a = _as2d(_as_array(A))

        def field(v):
            if isinstance(v, (float, np.floating)) and math.isnan(v):
                return ""                     # NaN is written as an empty field
            return _g15(v)

        lines = [delim.join(field(v) for v in row) for row in a]
        with open(path, "a" if mode == "append" else "w", newline="",
                  encoding="utf-8") as fh:
            fh.write("".join(ln + "\n" for ln in lines))

    def f_dlmwrite(self, filename, M, *args):
        append = False
        args = list(args)
        if "-append" in [a for a in args if isinstance(a, str)]:
            append = True
            args = [a for a in args if not (isinstance(a, str)
                                            and a == "-append")]
        delim, r, c, precision, newline = ",", 0, 0, None, "\n"
        keys = {"delimiter", "roffset", "coffset", "precision", "newline"}
        if args and not (isinstance(args[0], str)
                         and args[0].lower() in keys):
            delim = _delimiter(args[0], "dlmwrite") if args[0] != "" else ","
            args = args[1:]
            if len(args) >= 2 and not isinstance(args[0], str):
                r, c = _int_arg(args[0], "R"), _int_arg(args[1], "C")
                args = args[2:]
        opts = _options(args, {k: k for k in keys}, "dlmwrite")
        if "delimiter" in opts:
            delim = _delimiter(opts["delimiter"], "dlmwrite")
        r = _int_arg(opts.get("roffset", r), "roffset")
        c = _int_arg(opts.get("coffset", c), "coffset")
        precision = opts.get("precision", precision)
        if "newline" in opts:
            nl = str(opts["newline"]).lower()
            if nl not in ("pc", "unix"):
                raise MatlabError("dlmwrite: 'newline' must be 'pc' or "
                                  "'unix'.")
            newline = "\r\n" if nl == "pc" else "\n"
        self._write_dlm("dlmwrite", filename, M, delim, r, c, precision,
                        newline, append)

    def f_csvwrite(self, filename, M, r=0, c=0):
        self._write_dlm("csvwrite", filename, M, ",", _int_arg(r, "R"),
                        _int_arg(c, "C"), None, "\n", False)

    def _write_dlm(self, fn, filename, M, delim, r, c, precision, newline,
                   append):
        path = self.rt.resolve(filename)
        _refuse_spreadsheet(path, fn)
        if isinstance(M, (str, Cell, Struct, StructArray, Table)):
            raise MatlabError(f"{fn} writes numeric arrays only.")
        a = _as2d(_as_array(M))

        def fmt(v):
            if isinstance(v, (bool, np.bool_)):
                v = int(v)
            if isinstance(v, (complex, np.complexfloating)):
                im = v.imag
                return fmt(v.real) + ("+" if im >= 0 else "-") + \
                    fmt(abs(im)) + "i"
            v = float(v)
            if math.isnan(v):
                return "NaN"
            if math.isinf(v):
                return "Inf" if v > 0 else "-Inf"
            if isinstance(precision, str):
                return _mr._sprintf(precision, (v,))
            digits = 5 if precision is None else _int_arg(precision,
                                                         "precision")
            return f"{v:.{digits}g}"

        width = (a.shape[1] if a.size else 0) + c
        out = [delim * max(width - 1, 0)] * r
        out += [delim * c + delim.join(fmt(v) for v in row) for row in a]
        with open(path, "a" if append else "w", newline="",
                  encoding="utf-8") as fh:
            fh.write("".join(ln + newline for ln in out))

    # ── tables ─────────────────────────────────────────────────

    def f_readtable(self, filename, *args):
        opts = _options(args, {
            "delimiter": "Delimiter", "readvariablenames": "ReadVariableNames",
            "numheaderlines": "NumHeaderLines", "filetype": "FileType",
            "variablenamingrule": "VariableNamingRule",
            "texttype": "TextType"}, "readtable")
        path = self.rt.resolve(filename)
        _refuse_spreadsheet(path, "readtable")
        if str(opts.get("FileType", "text")).lower() not in ("text",
                                                             "delimitedtext"):
            raise MatlabError("readtable: Evans reads text files only.")
        if str(opts.get("TextType", "char")).lower() != "char":
            raise MatlabError("readtable: Evans reads text as char "
                              "('TextType', 'char') only.")
        rule = str(opts.get("VariableNamingRule", "modify")).lower()
        if rule not in ("modify", "preserve"):
            raise MatlabError("'VariableNamingRule' must be 'modify' or "
                              "'preserve'.")
        lines = _parse_lines(_read_text(path, filename))
        skip = _int_arg(opts.get("NumHeaderLines", 0), "NumHeaderLines")
        lines = [ln for ln in lines[skip:] if ln.strip()]
        delim = (_delimiter(opts["Delimiter"], "readtable")
                 if "Delimiter" in opts else _detect(lines))
        rows = [_split(ln, delim) for ln in lines]
        if "ReadVariableNames" in opts:
            header = _truth(opts["ReadVariableNames"])
        else:
            header = bool(rows) and _looks_like_header(rows)
        heads = rows.pop(0) if header and rows else None
        width = max([len(r) for r in rows] + [len(heads or [])], default=0)
        rows = [r + [""] * (width - len(r)) for r in rows]
        raw = list(heads or []) + [""] * (width - len(heads or []))
        raw = [h if h else f"Var{k + 1}" for k, h in enumerate(raw)] \
            if heads is not None else [f"Var{k + 1}" for k in range(width)]
        names = raw if rule == "preserve" else [make_valid_name(h)
                                                for h in raw]
        names = _unique(names)
        descriptions = []
        if names != raw:
            descriptions = [h if h != n else "" for h, n in zip(raw, names)]
            if heads is not None:
                print("Warning: Column headers from the file were modified "
                      "to make them valid MATLAB identifiers before creating "
                      "variable names for the table. The original column "
                      "headers are saved in the VariableDescriptions "
                      "property.\nSet 'VariableNamingRule' to 'preserve' to "
                      "use the original column headers as table variable "
                      "names.")
        data = []
        for k in range(width):
            fields = [r[k] for r in rows]
            nums = [_number(f) for f in fields]
            if all(v is not None or not f.strip()
                   for v, f in zip(nums, fields)):
                vals = [math.nan if v is None else v for v in nums]
                cplx = any(isinstance(v, complex) for v in vals)
                data.append(np.array(vals, dtype=complex if cplx else float))
            else:
                data.append(list(fields))
        return ColumnTable(names, data, descriptions, height=len(rows))

    @_named
    def f_writetable(self, T, filename=None, *args, names=None):
        if not isinstance(T, ColumnTable):
            raise MatlabError("writetable needs a table, such as one from "
                              "table, array2table or readtable.")
        if isinstance(filename, str) and filename.lower() in (
                "delimiter", "writevariablenames", "writemode",
                "filetype") and len(args) % 2 == 1:
            args = (filename, *args)
            filename = None
        opts = _options(args, {"delimiter": "Delimiter",
                               "writevariablenames": "WriteVariableNames",
                               "writemode": "WriteMode",
                               "filetype": "FileType"}, "writetable")
        if filename is None:
            name = names[0] if names and names[0] else None
            filename = f"{name}.txt" if name else "table.txt"
        path = self.rt.resolve(filename)
        _refuse_spreadsheet(path, "writetable")
        if str(opts.get("FileType", "text")).lower() != "text":
            raise MatlabError("writetable: Evans writes text files only.")
        delim = _delimiter(opts.get("Delimiter", ","), "writetable")
        mode = str(opts.get("WriteMode", "overwrite")).lower()
        if mode not in ("overwrite", "append"):
            raise MatlabError(f"writetable: 'WriteMode' '{mode}' is not "
                              f"supported for text files.")

        def quote(s: str) -> str:
            if any(ch in s for ch in (delim, "\n", "\r", '"')):
                return '"' + s.replace('"', '""') + '"'
            return s

        lines = []
        if _truth(opts.get("WriteVariableNames", True)) and mode != "append":
            lines.append(delim.join(quote(n) for n in T.columns))
        for i in range(T.height):
            fields = []
            for col in T._data:
                v = col[i]
                fields.append(_g15(v) if isinstance(col, np.ndarray)
                              else quote(v) if isinstance(v, str)
                              else _g15(v) if _is_number(v) else "")
            lines.append(delim.join(fields))
        with open(path, "a" if mode == "append" else "w", newline="",
                  encoding="utf-8") as fh:
            fh.write("".join(ln + "\n" for ln in lines))

    @_named
    def f_table(self, *args, names=None):
        names = list(names or [])
        values, opts = [], []
        for k, a in enumerate(args):
            if isinstance(a, str) and a.lower() in ("variablenames",
                                                    "rownames", "size",
                                                    "variabletypes"):
                opts = list(args[k:])
                break
            values.append(a)
        given = _options(opts, {"variablenames": "VariableNames",
                                "rownames": "RowNames"}, "table")
        if "RowNames" in given:
            raise MatlabError("table: 'RowNames' is not supported in Evans.")
        if "VariableNames" in given:
            var_names = _name_list(given["VariableNames"], len(values))
        else:
            var_names = [names[k] if k < len(names) and names[k]
                         else f"Var{k + 1}" for k in range(len(values))]
        data = [_as_column(v, k + 1) for k, v in enumerate(values)]
        return ColumnTable(var_names, data)

    def f_array2table(self, A, *args):
        given = _options(args, {"variablenames": "VariableNames",
                                "rownames": "RowNames"}, "array2table")
        if "RowNames" in given:
            raise MatlabError("array2table: 'RowNames' is not supported in "
                              "Evans.")
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
        var_names = (_name_list(given["VariableNames"], n)
                     if "VariableNames" in given
                     else [f"Var{k + 1}" for k in range(n)])
        return ColumnTable(var_names, data, height=height)

    def f_table2array(self, T):
        if not isinstance(T, ColumnTable):
            raise MatlabError("table2array needs a table.")
        if not T.columns:
            return np.zeros((T.height, 0))
        text = [T.is_text(k) for k in range(len(T.columns))]
        if all(text):
            return Cell((v for col in T._data for v in col), rows=T.height)
        if any(text):
            k = text.index(True)
            j = text.index(False)
            a, b = sorted((j, k))
            ta = "cell" if text[a] else "double"
            tb = "cell" if text[b] else "double"
            raise MatlabError(
                f"Unable to concatenate the table variables "
                f"'{T.columns[a]}' and '{T.columns[b]}', because their types "
                f"are {ta} and {tb}.")
        cols = T._data
        if all(c.dtype == bool for c in cols):
            m = np.column_stack(cols) if T.height else np.zeros((0, len(cols)),
                                                                 bool)
        else:
            m = np.column_stack([c.astype(complex if np.iscomplexobj(c)
                                          else float) for c in cols])
        return _normalise(m)

    def f_height(self, T):
        return _shape(T)[0]

    def f_width(self, T):
        return _shape(T)[1]

    def f_istable(self, x):
        return isinstance(x, Table)

    # ── fopen and friends ──────────────────────────────────────

    def _files(self) -> dict:
        table = getattr(self.rt, "_fids", None)
        if table is None:
            table = {}
            self.rt._fids = table
        return table

    def _file(self, fid) -> _OpenFile:
        try:
            key = int(np.asarray(fid, float).reshape(-1)[0]) \
                if not isinstance(fid, str) and np.size(fid) == 1 else None
        except (TypeError, ValueError):
            key = None
        f = self._files().get(key)
        if f is None:
            raise MatlabError(_INVALID_FID, "MATLAB:FileIO:InvalidFid")
        return f

    @_nargout
    def f_fopen(self, filename, permission="r", machinefmt="n",
                encoding="UTF-8", nargout=1):
        files = self._files()
        if isinstance(filename, str) and filename.lower() == "all" \
                and permission == "r":
            return np.array(sorted(files), dtype=float)
        if not isinstance(filename, str):
            f = self._file(filename)
            out = (f.name, f.permission, machinefmt, f.encoding)
            return out[0] if nargout <= 1 else out[:nargout]
        perm = _as_text(permission)
        mode = perm.replace("t", "").replace("b", "")
        if mode not in _PERMISSIONS:
            raise MatlabError("Invalid permission.")
        try:
            "".encode(encoding)
        except LookupError:
            raise MatlabError(f"The encoding '{encoding}' is not "
                              f"supported.") from None
        path = self.rt.resolve(filename)
        try:
            fh = open(path, _PERMISSIONS[mode])
        except OSError as exc:
            msg = os.strerror(exc.errno) if exc.errno else str(exc)
            return -1 if nargout <= 1 else (-1, msg)[:nargout]
        fid = 3
        while fid in files:
            fid += 1
        files[fid] = _OpenFile(fh, path, perm, "t" in perm,
                               _machine(machinefmt), encoding)
        return fid if nargout <= 1 else (fid, "")[:nargout] + \
            ("",) * max(nargout - 2, 0)

    def f_fclose(self, fid):
        files = self._files()
        if isinstance(fid, str):
            if fid.lower() != "all":
                raise MatlabError(_INVALID_FID, "MATLAB:FileIO:InvalidFid")
            for f in files.values():
                f.fh.close()
            files.clear()
            return 0
        f = self._file(fid)
        f.fh.close()
        del files[int(np.asarray(fid).reshape(-1)[0])]
        return 0

    def _readline(self, fid, keep: bool):
        f = self._file(fid)
        raw = f.fh.readline()
        if not raw:
            return -1
        text = raw.decode(f.encoding, errors="replace")
        if keep:
            return text.replace("\r\n", "\n") if f.text else text
        return text.rstrip("\n").rstrip("\r") if text.endswith("\n") \
            else text

    def f_fgetl(self, fid):
        return self._readline(fid, keep=False)

    def f_fgets(self, fid, nchar=None):
        if nchar is not None:
            raise MatlabError("fgets(fid, nchar) is not supported in Evans.")
        return self._readline(fid, keep=True)

    def f_feof(self, fid):
        f = self._file(fid)
        return f.fh.tell() >= f.size()

    def f_frewind(self, fid):
        self._file(fid).fh.seek(0)

    def f_ftell(self, fid):
        return self._file(fid).fh.tell()

    def f_fseek(self, fid, offset, origin="bof"):
        f = self._file(fid)
        where = {"bof": 0, "cof": 1, "eof": 2, -1: 0, 0: 1, 1: 2}
        key = origin.lower() if isinstance(origin, str) else int(origin)
        if key not in where:
            raise MatlabError("Invalid origin: use 'bof', 'cof' or 'eof'.")
        base = {0: 0, 1: f.fh.tell(), 2: f.size()}[where[key]]
        target = base + int(offset)
        if target < 0 or ("+" not in f.permission and "r" in f.permission
                          and target > f.size()):
            return -1
        f.fh.seek(target)
        return 0

    @_nargout
    def f_fprintf(self, *args, nargout=0):
        if not args:
            raise MatlabError("Not enough input arguments.")
        fid = 1
        first = args[0]
        if len(args) >= 2 and isinstance(args[1], str) and not isinstance(
                first, (str, bool, np.bool_)) and (
                _is_number(first) or (isinstance(first, np.ndarray)
                                      and first.size == 1)):
            fid, args = int(np.asarray(first).reshape(-1)[0].real), args[1:]
        elif isinstance(first, (int, float)) and not isinstance(
                first, bool) and first in (1, 2) and len(args) >= 2:
            fid, args = int(first), args[1:]
        fmt, rest = args[0], args[1:]
        text = _mr._sprintf(fmt if isinstance(fmt, str) else str(fmt), rest)
        if fid == 1:
            print(text, end="")
            n = len(text.encode("utf-8"))
        elif fid == 2:
            print(text, end="", file=sys.stderr)
            n = len(text.encode("utf-8"))
        else:
            f = self._file(fid)
            if f.text and os.name == "nt":
                text = text.replace("\n", "\r\n")
            data = text.encode(f.encoding, errors="replace")
            try:
                f.fh.write(data)
            except OSError:
                raise MatlabError(f"The file was opened with '{f.permission}'"
                                  f"; open it with 'w' or 'a' to write "
                                  f"to it.") from None
            n = len(data)
        return n if nargout >= 1 else None

    def _rest(self, f: _OpenFile) -> tuple[str, int]:
        start = f.fh.tell()
        return f.fh.read().decode(f.encoding, errors="replace"), start

    def _advance(self, f: _OpenFile, text: str, start: int, chars: int):
        f.fh.seek(start + len(text[:chars].encode(f.encoding,
                                                   errors="replace")))

    @_nargout
    def f_fscanf(self, fid, fmt, sizeA=None, nargout=1):
        f = self._file(fid)
        text, start = self._rest(f)
        limit = _limit(sizeA)
        values, chars_only, count, used = _fscanf(text, fmt, limit)
        self._advance(f, text, start, used)
        if chars_only:
            if sizeA is not None and np.size(sizeA) == 2:
                raise MatlabError("fscanf: Evans returns text from %s and %c "
                                  "as a row; a [m n] size is not supported "
                                  "for text.")
            out = "".join(chr(int(v)) for v in values)
        else:
            out = _shape_output(values, sizeA) if values else \
                np.zeros((0, 1) if sizeA is None else (0, 0))
        if nargout >= 2:
            return (out, count, "")[:nargout]
        return out

    @_nargout
    def f_textscan(self, source, fmt="%f", *args, nargout=1):
        repeat = math.inf
        if args and not isinstance(args[0], str):
            repeat = float(np.asarray(args[0], float).reshape(-1)[0])
            if repeat < 0:
                repeat = math.inf
            args = args[1:]
        opts = _options(args, {
            "delimiter": "Delimiter", "headerlines": "HeaderLines",
            "endofline": "EndOfLine", "multipledelimsasone":
                "MultipleDelimsAsOne", "collectoutput": "CollectOutput",
            "emptyvalue": "EmptyValue", "returnonerror": "ReturnOnError",
            "whitespace": "Whitespace"}, "textscan")
        f = None
        if isinstance(source, str):
            text, start = source, 0
        else:
            f = self._file(source)
            text, start = self._rest(f)
        pos = 0
        for _ in range(_int_arg(opts.get("HeaderLines", 0), "HeaderLines")):
            nl = text.find("\n", pos)
            pos = len(text) if nl < 0 else nl + 1
        delims = None
        if "Delimiter" in opts:
            d = opts["Delimiter"]
            items = list(d) if isinstance(d, Cell) else [d]
            delims = [_delimiter(x, "textscan") for x in items]
        empty = float(opts.get("EmptyValue", math.nan))
        many = _truth(opts.get("MultipleDelimsAsOne", False))
        ws = _mr._escapes(opts["Whitespace"]) if "Whitespace" in opts \
            else " \b\t"
        if delims:
            ws = "".join(c for c in ws if c not in "".join(delims))
        items = _scan_format(fmt, "textscan")
        convs = [it[1] for it in items if it[0] == "conv"]
        if not convs:
            raise MatlabError("textscan: the format has no conversions.")
        columns = [[] for m in convs if not m.group("skip")]
        kinds = []
        for m in convs:
            if m.group("skip"):
                continue
            c = m.group("conv")
            if c in ("s", "q", "c") or c.startswith("["):
                kinds.append("text")
            elif c in "diuneEgGf" or c[0] in "fdu":
                kinds.append("num")
            else:
                raise MatlabError(f"textscan: '%{c}' is not supported in "
                                  f"Evans.")

        def at_delim(p):
            for d in delims or []:
                if text.startswith(d, p):
                    return d
            return None

        def after_field(p):
            p = _skip_ws(text, p, ws)
            d = at_delim(p) if delims else None
            if d:
                p += len(d)
                if many:
                    while True:
                        q = _skip_ws(text, p, ws)
                        d2 = at_delim(q)
                        if not d2:
                            break
                        p = q + len(d2)
            return p, bool(d)

        rounds = 0
        last_delim = False
        done = False
        while rounds < repeat and not done:
            col = 0
            cycle_start = pos
            for item in items:
                if item[0] == "ws":
                    pos = _skip_ws(text, pos, ws + "\r\n")
                    continue
                if item[0] == "lit":
                    p = _skip_ws(text, pos, ws + "\r\n")
                    if text.startswith(item[1], p):
                        pos = p + len(item[1])
                        pos, last_delim = after_field(pos)
                        continue
                    done = True
                    break
                m = item[1]
                conv = m.group("conv")
                p = _skip_ws(text, pos, ws)
                empty_field = bool(delims) and (
                    at_delim(p) is not None
                    or (last_delim and (p >= len(text) or text[p] in "\r\n")))
                if not empty_field:
                    p = _skip_ws(text, p, ws + "\r\n")
                    if p >= len(text):
                        done = True
                        break
                if empty_field:
                    value = empty if conv not in ("s", "q", "c") else ""
                    end = p
                elif conv in ("s", "q") or conv.startswith("["):
                    if conv == "q" and text.startswith('"', p):
                        close = text.find('"', p + 1)
                        close = len(text) - 1 if close < 0 else close
                        value, end = text[p + 1:close], close + 1
                    else:
                        end = p
                        stops = "\r\n" + ("" if delims else ws)
                        while end < len(text) and text[end] not in stops \
                                and not (delims and at_delim(end)):
                            end += 1
                        value = text[p:end].rstrip(ws)
                        if conv.startswith("["):
                            mm = re.match(conv + "*", value)
                            value = mm.group()
                            end = p + len(value)
                elif conv == "c":
                    value, end = text[p], p + 1
                else:
                    mm = (_INT_RE if conv[0] in "diu" and conv != "u"
                          or conv in ("d", "i", "u") else _FLOAT_RE).match(
                              text, p)
                    if not mm:
                        done = True
                        break
                    value, end = _real(mm.group()), mm.end()
                pos, last_delim = after_field(end)
                if not m.group("skip"):
                    columns[col].append(value)
                    col += 1
            if pos == cycle_start:
                break
            rounds += 1
        if f is not None:
            self._advance(f, text, start, pos)
        out = []
        for kind, values in zip(kinds, columns):
            if kind == "num":
                a = np.array(values, dtype=float).reshape(-1, 1)
                out.append(a if a.size != 1 else _scalar(a[0, 0]))
            else:
                out.append(Cell(values, rows=len(values)))
        if _truth(opts.get("CollectOutput", False)):
            out = _collect(out, kinds)
        result = Cell(out, rows=1)
        if nargout >= 2:
            return result, len(text[:pos].encode("utf-8")) + start
        return result

    @_nargout
    def f_fread(self, fid, *args, nargout=1):
        f = self._file(fid)
        sizeA, precision = None, "uint8"
        rest = list(args)
        if rest and not isinstance(rest[0], str):
            sizeA = rest.pop(0)
        if rest:
            precision = rest.pop(0)
        if rest and not isinstance(rest[0], str):
            skip = rest.pop(0)
            if np.any(np.asarray(skip) != 0):
                raise MatlabError("fread: a skip value is not supported in "
                                  "Evans.")
        machine = _machine(rest.pop(0)) if rest else f.machine
        if rest:
            raise MatlabError("Too many input arguments.")
        code, as_char = _precision(precision, "fread")
        dtype = np.dtype(machine + code if code[1] != "1" else code)
        limit = _limit(sizeA)
        n = dtype.itemsize
        raw = f.fh.read() if math.isinf(limit) else f.fh.read(int(limit) * n)
        usable = len(raw) - len(raw) % n
        if usable < len(raw):
            f.fh.seek(usable - len(raw), 1)
        values = np.frombuffer(raw[:usable], dtype=dtype).astype(float)
        count = values.size
        if as_char:
            out = "".join(chr(int(v)) for v in values)
        elif count == 0:
            out = np.zeros((0, 1) if sizeA is None else (0, 0))
        else:
            out = _shape_output(values.tolist(), sizeA)
        return (out, count)[:nargout] if nargout >= 2 else out

    def f_fwrite(self, fid, A, precision="uint8", skip=0, machinefmt=None):
        f = self._file(fid)
        if np.any(np.asarray(skip) != 0):
            raise MatlabError("fwrite: a skip value is not supported in "
                              "Evans.")
        code, _ = _precision(precision, "fwrite")
        machine = _machine(machinefmt) if machinefmt is not None \
            else f.machine
        dtype = np.dtype(machine + code if code[1] != "1" else code)
        if isinstance(A, str):
            values = np.array([ord(c) for c in A], dtype=float)
        else:
            values = np.asarray(_column_major(A), dtype=float)
        if dtype.kind in "iu":
            info = np.iinfo(dtype)
            values = np.nan_to_num(values, nan=0.0)
            values = np.sign(values) * np.floor(np.abs(values) + 0.5)
            values = np.clip(values, info.min, info.max)
        data = values.astype(dtype).tobytes()
        try:
            f.fh.write(data)
        except OSError:
            raise MatlabError(f"The file was opened with '{f.permission}'; "
                              f"open it with 'w' or 'a' to write to "
                              f"it.") from None
        return values.size

    # ── JSON ───────────────────────────────────────────────────

    def f_jsondecode(self, text):
        if not isinstance(text, str):
            raise MatlabError("jsondecode needs JSON text as a char vector.")
        try:
            parsed = json.loads(text, parse_constant=_json_constant)
        except json.JSONDecodeError as exc:
            raise MatlabError(
                f"JSON syntax error at line {exc.lineno}, column {exc.colno} "
                f"(character {exc.pos + 1}): {exc.msg}.",
                "MATLAB:json:ExpectedValue") from None
        return _from_json(parsed)

    def f_jsonencode(self, value, *args):
        opts = _options(args, {"prettyprint": "PrettyPrint",
                               "convertinfandnan": "ConvertInfAndNaN"},
                        "jsonencode")
        data = _to_json(value, _truth(opts.get("ConvertInfAndNaN", True)))
        if _truth(opts.get("PrettyPrint", False)):
            text = json.dumps(data, indent=2, ensure_ascii=False)
        else:
            text = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        return text


def _json_constant(name: str):
    return {"NaN": math.nan, "Infinity": math.inf,
            "-Infinity": -math.inf}[name]


def _looks_like_header(rows: list[list[str]]) -> bool:
    """A first line of text over columns that hold numbers below it."""
    first, rest = rows[0], rows[1:]
    if any(_number(f) is not None for f in first):
        return False
    if not rest:
        return True
    for k in range(len(first)):
        below = [r[k] for r in rest if k < len(r) and r[k].strip()]
        if below and all(_number(f) is not None for f in below):
            return True
    # Every column is text: a header unless the first line looks like data
    # in the same shape — MATLAB treats it as names too.
    return True


def _name_list(value, n: int) -> list[str]:
    names = [value] if isinstance(value, str) else list(value) \
        if isinstance(value, (Cell, list)) else None
    if names is None or not all(isinstance(x, str) for x in names):
        raise MatlabError("'VariableNames' must be a cell array of char "
                          "vectors.")
    if len(names) != n:
        raise MatlabError(f"The VariableNames property must contain one name "
                          f"for each variable in the table ({n}).")
    return names


def _collect(out: list, kinds: list[str]) -> list:
    """textscan's CollectOutput: neighbouring columns of a kind, merged."""
    merged, k = [], 0
    while k < len(out):
        j = k
        while j + 1 < len(out) and kinds[j + 1] == kinds[k]:
            j += 1
        group = out[k:j + 1]
        if len(group) == 1:
            merged.append(group[0])
        elif kinds[k] == "num":
            cols = [np.asarray(g, float).reshape(-1, 1) for g in group]
            if len({c.shape[0] for c in cols}) > 1:
                merged.extend(group)
            else:
                merged.append(_normalise(np.hstack(cols)))
        else:
            if len({len(g) for g in group}) > 1:
                merged.extend(group)
            else:
                merged.append(Cell([v for g in group for v in g],
                                   rows=len(group[0])))
        k = j + 1
    return merged


__all__ = ["ColumnTable", "FileLibrary", "make_valid_name"]
