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
)
from .tables import ColumnTable  # noqa: E402

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
    """Refuse the spreadsheet formats openpyxl cannot open (.xls, .ods)."""
    if _ext(path) in _SPREADSHEET and _ext(path) not in _XLSX:
        raise MatlabError(f"{fn}: Evans reads Excel workbooks (.xlsx, "
                          f".xlsm) but not {_ext(path)} files. Save the "
                          f"sheet as .xlsx or .csv and read that.")


# ── Excel workbooks, through openpyxl ──────────────────────────
# A sheet is read into the same grid of text fields a delimited file is
# split into, so readmatrix and readtable treat both alike: a header row is
# recognised, numbers are parsed and blanks are NaN the same way.

_XLSX = (".xlsx", ".xlsm", ".xltx", ".xltm")


def _is_xlsx(path: str, opts: dict | None = None) -> bool:
    return _ext(path) in _XLSX or str((opts or {}).get(
        "FileType", "")).lower() == "spreadsheet"


def _openpyxl():
    try:
        import openpyxl
    except ImportError:                                 # pragma: no cover
        raise MatlabError("Reading and writing .xlsx needs the openpyxl "
                          "package: pip install openpyxl.") from None
    return openpyxl


def _xl_field(v) -> str:
    """A cell's value as the text a delimited file would hold."""
    if v is None:
        return ""
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, float):
        return repr(v)
    return str(v)


def _pick_sheet(wb, sheet, fn: str):
    if sheet is None or (not isinstance(sheet, str) and _numel_of(sheet) == 0):
        return wb.worksheets[0]
    if isinstance(sheet, str):
        if sheet in wb.sheetnames:
            return wb[sheet]
        raise MatlabError(f"{fn}: the workbook has no sheet '{sheet}'; it "
                          f"has {', '.join(wb.sheetnames)}.")
    k = int(np.asarray(sheet, float).reshape(-1)[0])
    if not 1 <= k <= len(wb.worksheets):
        raise MatlabError(f"{fn}: sheet {k} does not exist; the workbook "
                          f"has {len(wb.worksheets)}.")
    return wb.worksheets[k - 1]


def _numel_of(x) -> int:
    return int(np.size(x))


def _sheet_rows(path: str, shown, sheet, fn: str) -> list[list[str]]:
    """Every row of one sheet from A1, as text fields, blanks trimmed."""
    openpyxl = _openpyxl()
    if not os.path.isfile(path):
        _read_text(path, shown)                         # raises the error
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
    except Exception as exc:                             # noqa: BLE001
        raise MatlabError(f"{fn}: '{_as_text(shown)}' is not a workbook "
                          f"Evans can read ({exc}).") from None
    try:
        ws = _pick_sheet(wb, sheet, fn)
        rows = [[_xl_field(v) for v in row]
                for row in ws.iter_rows(min_row=1, min_col=1,
                                        values_only=True)]
    finally:
        wb.close()
    for row in rows:
        while row and not row[-1].strip():
            row.pop()
    while rows and not rows[-1]:
        rows.pop()
    return rows


def _trim_left(rows: list[list[str]]) -> list[list[str]]:
    """Drop the empty columns before the data starts, as MATLAB does."""
    filled = [r for r in rows if r]
    lead = min((next(k for k, f in enumerate(r) if f.strip())
                for r in filled if any(f.strip() for f in r)), default=0)
    return [r[lead:] for r in rows]


def _write_sheet(path: str, grid: list[list], sheet, rng, mode: str,
                 fn: str) -> None:
    """
    Write a grid of values (numbers, text, ``None`` for blank) to a sheet.

    ``mode`` is MATLAB's WriteMode for spreadsheets: ``inplace`` (the
    default) writes over the cells it covers and keeps the rest of the
    workbook; ``overwritesheet`` clears the sheet first; ``append`` writes
    below its last row; ``replacefile`` starts a new workbook.
    """
    openpyxl = _openpyxl()
    mode = mode.lower()
    if mode not in ("inplace", "overwritesheet", "append", "replacefile"):
        raise MatlabError(f"{fn}: 'WriteMode' '{mode}' is not one of "
                          f"inplace, overwritesheet, append, replacefile.")
    fresh = mode == "replacefile" or not os.path.isfile(path)
    if fresh:
        wb = openpyxl.Workbook()
        if sheet is not None and not isinstance(sheet, str):
            k = int(np.asarray(sheet, float).reshape(-1)[0])
            for n in range(2, k + 1):
                wb.create_sheet(f"Sheet{n}")
        else:
            wb.active.title = sheet if isinstance(sheet, str) else "Sheet1"
    else:
        wb = openpyxl.load_workbook(path)
    try:
        if isinstance(sheet, str) and sheet not in wb.sheetnames:
            ws = wb.create_sheet(sheet)
        else:
            ws = _pick_sheet(wb, sheet, fn)
        if mode == "overwritesheet":
            ws.delete_rows(1, ws.max_row)
        r0, c0 = 1, 1
        if rng is not None:
            r0, c0, _r2, _c2 = _spreadsheet_range(str(rng))
        if mode == "append" and ws.max_row > 1 or (
                mode == "append" and ws.cell(1, 1).value is not None):
            r0 = ws.max_row + 1
        for i, row in enumerate(grid):
            for j, v in enumerate(row):
                ws.cell(r0 + i, c0 + j).value = v
        wb.save(path)
    except PermissionError:
        raise MatlabError(f"{fn}: cannot write '{path}'. Is it open in "
                          f"Excel?") from None
    finally:
        wb.close()


def _xl_value(v):
    """A number for a cell: NaN is left blank, as writematrix leaves it."""
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (complex, np.complexfloating)):
        raise MatlabError("Complex numbers cannot be written to a "
                          "spreadsheet.")
    v = float(v)
    if math.isnan(v):
        return None
    return int(v) if v.is_integer() and abs(v) < 2 ** 53 else v


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


def _empty_arg(x) -> bool:
    return x is None or (not isinstance(x, str) and np.size(x) == 0) \
        or x == ""


def _trim_outer(grid: np.ndarray, filled: np.ndarray) -> np.ndarray:
    """Cut away the outer rows and columns where nothing is filled."""
    if not filled.size or not filled.any():
        return grid[:0, :0] if grid.ndim == 2 else grid
    rows = np.nonzero(filled.any(axis=1))[0]
    cols = np.nonzero(filled.any(axis=0))[0]
    return grid[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]


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
                               "outputtype": "OutputType",
                               "sheet": "Sheet"}, "readmatrix")
        path = self.rt.resolve(filename)
        _refuse_spreadsheet(path, "readmatrix")
        if str(opts.get("FileType", "text")).lower() not in (
                "text", "delimitedtext", "spreadsheet"):
            raise MatlabError("readmatrix: 'FileType' must be 'text' or "
                              "'spreadsheet'.")
        if str(opts.get("OutputType", "double")).lower() != "double":
            raise MatlabError("readmatrix: Evans reads numbers as double "
                              "only ('OutputType', 'double').")
        if _is_xlsx(path, opts):
            sheet = _sheet_rows(path, filename, opts.get("Sheet"),
                                "readmatrix")
            if "Range" in opts:
                rows = _apply_range(sheet, opts["Range"])
            else:
                skip = _int_arg(opts.get("NumHeaderLines", 0),
                                "NumHeaderLines")
                rows = _trim_left([r for r in sheet[skip:] if r])
                if "NumHeaderLines" not in opts:
                    while rows and all(_number(f) is None for f in rows[0]):
                        rows.pop(0)
            return _result(_numeric_grid(rows, math.nan))
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
                               "filetype": "FileType", "sheet": "Sheet",
                               "range": "Range"}, "writematrix")
        if filename is None:
            name = names[0] if names and names[0] else None
            filename = f"{name}.txt" if name else "matrix.txt"
        path = self.rt.resolve(filename)
        _refuse_spreadsheet(path, "writematrix")
        ftype = str(opts.get("FileType", "text")).lower()
        if _is_xlsx(path, opts):
            if isinstance(A, (str, Cell, Struct, StructArray, Table)):
                raise MatlabError("writematrix writes numeric or logical "
                                  "arrays; use writetable for a table.")
            grid = [[_xl_value(v) for v in row]
                    for row in _as2d(_as_array(A))]
            _write_sheet(path, grid, opts.get("Sheet"), opts.get("Range"),
                         str(opts.get("WriteMode", "inplace")),
                         "writematrix")
            return None
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
            "texttype": "TextType", "sheet": "Sheet",
            "range": "Range"}, "readtable")
        path = self.rt.resolve(filename)
        _refuse_spreadsheet(path, "readtable")
        if str(opts.get("FileType", "text")).lower() not in (
                "text", "delimitedtext", "spreadsheet"):
            raise MatlabError("readtable: 'FileType' must be 'text' or "
                              "'spreadsheet'.")
        if str(opts.get("TextType", "char")).lower() != "char":
            raise MatlabError("readtable: Evans reads text as char "
                              "('TextType', 'char') only.")
        rule = str(opts.get("VariableNamingRule", "modify")).lower()
        if rule not in ("modify", "preserve"):
            raise MatlabError("'VariableNamingRule' must be 'modify' or "
                              "'preserve'.")
        skip = _int_arg(opts.get("NumHeaderLines", 0), "NumHeaderLines")
        if _is_xlsx(path, opts):
            rows = _sheet_rows(path, filename, opts.get("Sheet"),
                               "readtable")
            rows = (_apply_range(rows, opts["Range"]) if "Range" in opts
                    else _trim_left(rows))
            rows = [r for r in rows[skip:] if any(f.strip() for f in r)]
        else:
            lines = _parse_lines(_read_text(path, filename))
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
                               "filetype": "FileType", "sheet": "Sheet",
                               "range": "Range"}, "writetable")
        if filename is None:
            name = names[0] if names and names[0] else None
            filename = f"{name}.txt" if name else "table.txt"
        path = self.rt.resolve(filename)
        _refuse_spreadsheet(path, "writetable")
        data = [c.texts() if hasattr(c, "texts") else c for c in T._data]
        if _is_xlsx(path, opts):
            mode = str(opts.get("WriteMode", "inplace"))
            grid = []
            if _truth(opts.get("WriteVariableNames", True)) \
                    and mode.lower() != "append":
                grid.append(list(T.columns))
            for i in range(T.height):
                grid.append([_xl_value(col[i]) if isinstance(col, np.ndarray)
                             else col[i] if isinstance(col[i], str)
                             else _xl_value(col[i]) if _is_number(col[i])
                             else None for col in data])
            _write_sheet(path, grid, opts.get("Sheet"), opts.get("Range"),
                         mode, "writetable")
            return None
        if str(opts.get("FileType", "text")).lower() != "text":
            raise MatlabError("writetable: 'FileType' must be 'text' or "
                              "'spreadsheet'.")
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
            for col in data:
                v = col[i]
                fields.append(_g15(v) if isinstance(col, np.ndarray)
                              else quote(v) if isinstance(v, str)
                              else _g15(v) if _is_number(v) else "")
            lines.append(delim.join(fields))
        with open(path, "a" if mode == "append" else "w", newline="",
                  encoding="utf-8") as fh:
            fh.write("".join(ln + "\n" for ln in lines))

    @_nargout
    def f_xlsread(self, filename, *args, nargout=1):
        """
        ``[num, txt, raw] = xlsread(file, sheet, range)``. ``num`` holds the
        numbers (text is NaN), ``txt`` the text ('' where a number is) and
        ``raw`` both; ``num`` and ``txt`` lose their empty outer rows and
        columns, as MATLAB's do.
        """
        args = list(args)
        sheet = rng = None
        if len(args) == 1 and isinstance(args[0], str) and re.fullmatch(
                r"\s*[A-Za-z]+\d+\s*((:|\.\.)\s*[A-Za-z]+\d+\s*)?",
                args[0]):
            rng = args[0]
        else:
            sheet = args[0] if args else None
            rng = args[1] if len(args) > 1 and not _empty_arg(args[1]) \
                else None
        path = self.rt.resolve(filename)
        if _ext(path) == "":
            path += ".xlsx"
        _refuse_spreadsheet(path, "xlsread")
        rows = _sheet_rows(path, filename, sheet, "xlsread")
        if rng is not None:
            rows = _apply_range(rows, rng)
        width = max((len(r) for r in rows), default=0)
        rows = [r + [""] * (width - len(r)) for r in rows]
        nums = [[_number(f) for f in r] for r in rows]
        num = np.array([[math.nan if v is None or isinstance(v, complex)
                         else v for v in r] for r in nums], float) \
            if rows and width else np.zeros((0, 0))
        num = _trim_outer(num, ~np.isnan(num))
        text = [[f if v is None else "" for f, v in zip(r, n)]
                for r, n in zip(rows, nums)]
        filled = np.array([[bool(f) for f in r] for r in text], bool) \
            if rows and width else np.zeros((0, 0), bool)
        txt_grid = _trim_outer(np.array(text, dtype=object).reshape(
            len(rows), width), filled)
        txt = Cell.from_grid([list(r) for r in txt_grid])
        raw = Cell.from_grid([[(v if v is not None else f if f else math.nan)
                               for f, v in zip(r, n)]
                              for r, n in zip(rows, nums)])
        return (num, txt, raw)[:max(nargout, 1)] if nargout > 1 else num

    def f_xlswrite(self, filename, A, *args):
        """``xlswrite(file, A, sheet, range)``: numbers or a cell array."""
        args = list(args)
        sheet = rng = None
        if len(args) == 1 and isinstance(args[0], str) and \
                _CELL_REF.match(args[0].strip()) and not \
                args[0].strip().isalpha():
            rng = args[0]
        elif args:
            sheet = args[0]
            rng = args[1] if len(args) > 1 else None
        path = self.rt.resolve(filename)
        if _ext(path) == "":
            path += ".xlsx"
        _refuse_spreadsheet(path, "xlswrite")
        if isinstance(A, Cell):
            grid = [[v if isinstance(v, str) else None if (
                     isinstance(v, np.ndarray) and v.size == 0)
                     else _xl_value(_scalar(np.asarray(v).reshape(-1)[0]))
                     for v in row] for row in A.grid()]
        elif isinstance(A, str):
            grid = [[A]]
        else:
            grid = [[_xl_value(v) for v in row]
                    for row in _as2d(_as_array(A))]
        _write_sheet(path, grid, sheet, rng, "inplace", "xlswrite")

    def f_sheetnames(self, filename):
        """The names of a workbook's sheets, as a column."""
        path = self.rt.resolve(filename)
        _refuse_spreadsheet(path, "sheetnames")
        if not os.path.isfile(path):
            _read_text(path, filename)
        wb = _openpyxl().load_workbook(path, read_only=True)
        try:
            names = list(wb.sheetnames)
        finally:
            wb.close()
        return Cell(names, rows=len(names))

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
