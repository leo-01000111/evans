"""
Text.
=====
Splitting, joining, searching and padding character vectors and cells of them.

A mixin of :class:`.matlab_runtime._Library`: each ``f_<name>`` method is
the MATLAB function ``<name>``. It is imported by :mod:`.matlab_runtime`
just before ``_Library`` is defined, so the helpers above that line can be
imported from it by name; anything defined further down is reached through
the module (``_mr._sprintf``) at call time. Import :mod:`.matlab_runtime` first, never this module on
its own: the two import each other.

Text here is a char vector (a Python ``str``) or a cell of them (a cellstr).
A function that maps text to text keeps a cell's shape; one that answers a
yes/no question per string returns a logical array of the cell's shape.
Evans has no string arrays yet, so ``"..."`` is char and ``split`` returns a
cell where MATLAB returns a string array.
"""

from __future__ import annotations

import re

import numpy as np

from . import matlab_runtime as _mr  # noqa: F401
from .matlab_runtime import (
    Cell,
    MatlabError,
    Struct,
    StructArray,
    _nargout,  # noqa: F401
    _normalise,
)

# ──────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────

#: Whitespace that strtrim keeps: MATLAB calls these "significant".
_SIGNIFICANT = "\x85\xa0  "
_TRIM = "".join(chr(c) for c in range(0x3000) if chr(c).isspace()
                and chr(c) not in _SIGNIFICANT) + "\x00"
#: strsplit's and split's default delimiters.
_WHITESPACE = [" ", "\f", "\n", "\r", "\t", "\v"]


def _is_cellstr(x) -> bool:
    return isinstance(x, Cell) and all(isinstance(v, str) for v in x)


def _texts(x, fname: str, what: str = "First argument") -> list[str]:
    """The strings of a char vector or cellstr, column by column."""
    if isinstance(x, str):
        return [x]
    if _is_cellstr(x):
        return list(x)
    raise MatlabError(f"{what} of {fname} must be a character vector or a "
                      "cell array of character vectors.")


def _map(x, fn, fname: str):
    """``fn`` over a char vector, or over each string of a cellstr."""
    if isinstance(x, str):
        return fn(x)
    if _is_cellstr(x):
        return Cell([fn(v) for v in x], rows=x.rows)
    raise MatlabError(f"Input to {fname} must be a character vector or a "
                      "cell array of character vectors.")


def _logical_shaped(x, values: list):
    """A logical scalar for char ``x``, an array of the cell's shape else."""
    if isinstance(x, str):
        return bool(values[0])
    r, c = x.dims
    a = np.array(values, dtype=bool).reshape((c, r)).T if values \
        else np.zeros((0, 0), dtype=bool)
    return _normalise(a)


def _bool_row(values) -> np.ndarray:
    return np.array(list(values), dtype=bool)


def _row(values) -> np.ndarray:
    return np.array(list(values), dtype=float)


def _truth(v) -> bool:
    if isinstance(v, np.ndarray):
        return bool(v.size and np.all(v))
    return bool(v)


def _name_value(args, fname: str, names: dict) -> dict:
    """``'Name', value`` pairs: ``names`` maps lower-case names to defaults."""
    out = dict(names)
    if len(args) % 2:
        raise MatlabError(f"{fname}: every option name needs a value.")
    for k in range(0, len(args), 2):
        key = args[k]
        if not isinstance(key, str) or key.lower() not in names:
            raise MatlabError(f"{fname} does not have an option "
                              f"'{key}'.")
        out[key.lower()] = args[k + 1]
    return out


def _cell_row(items) -> Cell:
    items = list(items)
    return Cell(items, rows=1 if items else 0)


def _cell_column(items) -> Cell:
    items = list(items)
    return Cell(items, rows=len(items))


def _delimiters(delim, fname: str) -> list[str]:
    if isinstance(delim, str):
        out = [delim]
    elif _is_cellstr(delim):
        out = list(delim)
    else:
        raise MatlabError(f"The delimiter of {fname} must be a character "
                          "vector or a cell array of character vectors.")
    return out


def _escaped(text: str) -> str:
    """The escape sequences strsplit and strjoin read in a delimiter."""
    return re.sub(r"\\([\\0abfnrtv])",
                  lambda m: "\0" if m.group(1) == "0"
                  else _mr._ESCAPES[m.group(1)], text)


def _split_pattern(delims: list[str], collapse: bool, regex: bool) -> str:
    parts = delims if regex else [re.escape(d) for d in
                                  sorted(delims, key=len, reverse=True)]
    alt = "|".join(_py_regex(p) if regex else p for p in parts)
    return f"(?:{alt})+" if collapse else f"(?:{alt})"


def _split_text(s: str, pattern: str):
    pieces, matches, last = [], [], 0
    for m in re.finditer(pattern, s, re.DOTALL):
        if m.end() == m.start():
            continue
        pieces.append(s[last:m.start()])
        matches.append(m.group(0))
        last = m.end()
    pieces.append(s[last:])
    return pieces, matches


# ──────────────────────────────────────────────────────────────
#  MATLAB regular expressions → Python's
# ──────────────────────────────────────────────────────────────

def _py_regex(expr: str) -> str:
    """
    Translate the parts of MATLAB's regex syntax Python spells differently:
    ``(?<name>…)`` → ``(?P<name>…)``, ``\\k<name>`` → ``(?P=name)``,
    ``\\<`` / ``\\>`` (word start/end) and ``\\x{hh}`` / ``\\o{oo}``.
    """
    out: list[str] = []
    i, n, in_class = 0, len(expr), False
    while i < n:
        ch = expr[i]
        if ch == "\\" and i + 1 < n:
            nxt = expr[i + 1]
            if not in_class and nxt == "<":
                out.append(r"\b(?=\w)")
                i += 2
                continue
            if not in_class and nxt == ">":
                out.append(r"\b(?<=\w)")
                i += 2
                continue
            if nxt == "k" and expr.startswith("<", i + 2):
                end = expr.find(">", i + 3)
                if end > 0:
                    out.append(f"(?P={expr[i + 3:end]})")
                    i = end + 1
                    continue
            if nxt in "xo" and expr.startswith("{", i + 2):
                end = expr.find("}", i + 3)
                if end > 0:
                    code = int(expr[i + 3:end], 16 if nxt == "x" else 8)
                    out.append(re.escape(chr(code)))
                    i = end + 1
                    continue
            out.append(expr[i:i + 2])
            i += 2
            continue
        if in_class:
            if ch == "]":
                in_class = False
            out.append(ch)
            i += 1
            continue
        if ch == "[":
            in_class = True
            out.append(ch)
            i += 1
            # A ']' first in the class (after an optional '^') is literal.
            if expr.startswith("^", i):
                out.append("^")
                i += 1
            if expr.startswith("]", i):
                out.append(r"\]")
                i += 1
            continue
        if expr.startswith("(?<", i) and i + 3 < n and expr[i + 3] not in "=!":
            out.append("(?P<")
            i += 3
            continue
        out.append(ch)
        i += 1
    return "".join(out)


_REGEX_OUTPUTS = ("start", "end", "tokenextents", "match", "tokens",
                  "names", "split")
_REGEX_FLAGS = {"matchcase", "ignorecase", "emptymatch", "noemptymatch",
                "dotall", "dotexceptnewline", "stringanchors", "lineanchors",
                "literalspacing", "freespacing", "warnings", "once",
                "forcecelloutput"}


def _regex_options(options, fname: str, case_default: bool):
    flags = {"ignorecase": case_default, "emptymatch": False,
             "dotall": True, "lineanchors": False, "freespacing": False,
             "once": False, "forcecelloutput": False}
    outputs: list[str] = []
    for opt in options:
        if not isinstance(opt, str):
            raise MatlabError(f"Options of {fname} must be character "
                              "vectors.")
        key = opt.lower()
        if key in _REGEX_OUTPUTS:
            if key not in outputs:
                outputs.append(key)
        elif key in _REGEX_FLAGS:
            if key == "matchcase":
                flags["ignorecase"] = False
            elif key == "noemptymatch":
                flags["emptymatch"] = False
            elif key == "dotexceptnewline":
                flags["dotall"] = False
            elif key == "stringanchors":
                flags["lineanchors"] = False
            elif key == "literalspacing":
                flags["freespacing"] = False
            elif key != "warnings":
                flags[key] = True
        else:
            raise MatlabError(f"'{opt}' is not an option of {fname}.")
    return flags, outputs


def _compile(expr, flags: dict, fname: str) -> re.Pattern:
    if not isinstance(expr, str):
        raise MatlabError(f"The expression of {fname} must be a character "
                          "vector.")
    f = 0
    if flags["ignorecase"]:
        f |= re.IGNORECASE
    if flags["dotall"]:
        f |= re.DOTALL
    if flags["lineanchors"]:
        f |= re.MULTILINE
    if flags["freespacing"]:
        f |= re.VERBOSE
    try:
        return re.compile(_py_regex(expr), f)
    except re.error as exc:
        raise MatlabError(f"Invalid regular expression '{expr}': {exc}.",
                          "MATLAB:regexp:invalidPattern") from None


def _matches(pattern: re.Pattern, s: str, flags: dict) -> list[re.Match]:
    found = [m for m in pattern.finditer(s)
             if flags["emptymatch"] or m.end() > m.start()]
    return found[:1] if flags["once"] else found


def _token_texts(m: re.Match) -> list[str]:
    if not m.re.groups:
        return [m.group(0)]
    return [g if g is not None else "" for g in m.groups()]


def _token_extents(m: re.Match) -> np.ndarray:
    if not m.re.groups:
        return np.array([[m.start() + 1, m.end()]], dtype=float)
    rows = []
    for k in range(1, m.re.groups + 1):
        a, b = m.span(k)
        rows.append([a + 1, b] if a >= 0 else [m.start() + 1, m.start()])
    return np.array(rows, dtype=float)


def _regexp_outputs(pattern: re.Pattern, s: str, flags: dict) -> dict:
    """All seven outputs of regexp for one string."""
    found = _matches(pattern, s, flags)
    names = list(pattern.groupindex)

    def struct_of(m):
        return Struct({k: (m.group(k) or "") for k in names})

    pieces, last = [], 0
    for m in found:
        pieces.append(s[last:m.start()])
        last = m.end()
    pieces.append(s[last:])
    if flags["once"]:
        m = found[0] if found else None
        return {
            "start": m.start() + 1 if m else np.zeros(0),
            "end": m.end() if m else np.zeros(0),
            "tokenextents": _normalise(_token_extents(m)) if m
            else np.zeros((0, 0)),
            "match": m.group(0) if m else "",
            "tokens": _cell_row(_token_texts(m)) if m else Cell(),
            "names": (struct_of(m) if names else Struct()) if m
            else (StructArray() if names else Struct()),
            "split": _cell_row(pieces),
        }
    if names:
        structs = [struct_of(m) for m in found]
        named = structs[0] if len(structs) == 1 else StructArray(structs)
    else:
        named = Struct()
    return {
        "start": _row(m.start() + 1 for m in found),
        "end": _row(m.end() for m in found),
        "tokenextents": _cell_row(_normalise(_token_extents(m))
                                  for m in found),
        "match": _cell_row(m.group(0) for m in found),
        "tokens": _cell_row(_cell_row(_token_texts(m)) for m in found),
        "names": named,
        "split": _cell_row(pieces),
    }


def _replacement(m: re.Match, template: str) -> str:
    """MATLAB's ``$0``, ``$N``, ``$<name>`` and escapes in a replacement."""
    out: list[str] = []
    i, n = 0, len(template)
    while i < n:
        ch = template[i]
        if ch == "\\" and i + 1 < n:
            nxt = template[i + 1]
            out.append(_mr._ESCAPES.get(nxt, nxt) if nxt != "$" else "$")
            i += 2
        elif ch == "$" and i + 1 < n and template[i + 1].isdigit():
            k = int(template[i + 1])
            out.append((m.group(k) or "") if k <= m.re.groups or k == 0
                       else "")
            i += 2
        elif ch == "$" and template.startswith("<", i + 1):
            end = template.find(">", i + 2)
            name = template[i + 2:end]
            if end < 0 or name not in m.re.groupindex:
                raise MatlabError(f"regexprep: no token named '{name}'.")
            out.append(m.group(name) or "")
            i = end + 1
        elif ch == "$" and template.startswith("{", i + 1):
            raise MatlabError("regexprep: Evans does not support dynamic "
                              "replacement expressions ${...}.")
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _pattern_list(pattern, fname: str) -> list[str]:
    if isinstance(pattern, str):
        return [pattern]
    if _is_cellstr(pattern):
        return list(pattern)
    raise MatlabError("Search term must be a character vector or a cell "
                      f"array of character vectors ({fname}).")


def _search(x, pattern, args, fname: str, test):
    if not (isinstance(x, str) or _is_cellstr(x)):
        raise MatlabError("First argument must be text.")
    patterns = _pattern_list(pattern, fname)
    opts = _name_value(args, fname, {"ignorecase": False})
    fold = _truth(opts["ignorecase"])
    if fold:
        patterns = [p.lower() for p in patterns]
    values = []
    for s in _texts(x, fname):
        s = s.lower() if fold else s
        values.append(any(test(s, p) for p in patterns))
    return _logical_shaped(x, values)


_STRPROP = {
    "alpha": str.isalpha,
    "digit": lambda c: "0" <= c <= "9",
    "alphanum": lambda c: c.isalpha() or "0" <= c <= "9",
    "lower": str.islower,
    "upper": str.isupper,
    "wspace": str.isspace,
    "punct": lambda c: c.isprintable() and not c.isspace()
    and not c.isalnum(),
    "cntrl": lambda c: ord(c) < 32 or ord(c) == 127,
    "xdigit": lambda c: c in "0123456789abcdefABCDEF",
    "graphic": lambda c: c.isprintable() and not c.isspace(),
    "graph": lambda c: c.isprintable() and not c.isspace(),
    "print": lambda c: c.isprintable(),
    "ascii": lambda c: ord(c) < 128,
}


# ──────────────────────────────────────────────────────────────
#  The library
# ──────────────────────────────────────────────────────────────

class TextLibrary:
    """strsplit, regexp, contains and the rest."""

    # ── case, trimming, replacing ───────────────────────────────

    def f_upper(self, s):
        return _map(s, str.upper, "upper")

    def f_lower(self, s):
        return _map(s, str.lower, "lower")

    def f_strtrim(self, s):
        if not (isinstance(s, str) or _is_cellstr(s)):
            raise MatlabError("Input should be a string, character array, "
                              "or cell array of character arrays.")
        return _map(s, lambda t: t.strip(_TRIM), "strtrim")

    def f_deblank(self, s):
        return _map(s, lambda t: t.rstrip(_TRIM + _SIGNIFICANT), "deblank")

    def f_blanks(self, n):
        return " " * int(_mr._scalar_of(n))

    def f_strrep(self, s, old, new):
        """
        Every occurrence, overlapping ones included, as MATLAB's does:
        ``strrep('2222', '22', '*')`` is ``'***'``.
        """
        if not isinstance(old, str) or not isinstance(new, str):
            raise MatlabError("strrep: Evans supports only character vectors "
                              "for the old and new text.")

        def replace(t: str) -> str:
            if not old:
                return t
            starts = {i for i in range(len(t) - len(old) + 1)
                      if t.startswith(old, i)}
            out, covered = [], 0
            for i, ch in enumerate(t):
                if i in starts:
                    out.append(new)
                    covered = i + len(old)
                elif i >= covered:
                    out.append(ch)
            return "".join(out)

        return _map(s, replace, "strrep")

    # ── splitting and joining ──────────────────────────────────

    @_nargout
    def f_strsplit(self, s, delimiter=None, *args, nargout=1):
        if not isinstance(s, str):
            raise MatlabError("First input must be either a character vector "
                              "or a string scalar.")
        if isinstance(delimiter, str) and delimiter.lower() in (
                "collapsedelimiters", "delimitertype") and len(args) % 2:
            args = (delimiter, *args)
            delimiter = None
        opts = _name_value(args, "strsplit", {"collapsedelimiters": True,
                                              "delimitertype": "simple"})
        kind = str(opts["delimitertype"]).lower()
        if kind not in ("simple", "regularexpression"):
            raise MatlabError("DelimiterType must be 'Simple' or "
                              "'RegularExpression'.")
        regex = kind == "regularexpression"
        delims = _WHITESPACE if delimiter is None \
            else _delimiters(delimiter, "strsplit")
        if not regex:
            delims = [_escaped(d) for d in delims]
        pattern = _split_pattern(delims, _truth(opts["collapsedelimiters"]),
                                 regex)
        pieces, matches = _split_text(s, pattern)
        if max(nargout, 1) >= 2:
            return _cell_row(pieces), _cell_row(matches)
        return _cell_row(pieces)

    def f_strjoin(self, c, delimiter=" "):
        if not _is_cellstr(c) or min(c.dims) > 1:
            raise MatlabError("The first input must be a 1xN cell array of "
                              "character vectors.")
        items = list(c)
        if isinstance(delimiter, str):
            return _escaped(delimiter).join(items)
        if _is_cellstr(delimiter):
            if len(delimiter) != max(len(items) - 1, 0):
                raise MatlabError("The number of delimiters must be one less "
                                  "than the number of elements to join.")
            out = items[:1]
            for d, item in zip(delimiter, items[1:]):
                out += [d, item]
            return "".join(out)
        raise MatlabError("The delimiter must be a character vector or a "
                          "cell array of character vectors.")

    @_nargout
    def f_split(self, s, delimiter=None, *args, nargout=1):
        """MATLAB returns a string array; Evans a cell of char, same shape."""
        if isinstance(delimiter, str) and delimiter.lower() == \
                "collapsedelimiters" and len(args) == 1:
            args = (delimiter, *args)
            delimiter = None
        opts = _name_value(args, "split", {"collapsedelimiters": True})
        delims = _WHITESPACE if delimiter is None \
            else _delimiters(delimiter, "split")
        pattern = _split_pattern(delims, _truth(opts["collapsedelimiters"]),
                                 False)
        if isinstance(s, str):
            pieces, matches = _split_text(s, pattern)
            out = (_cell_column(pieces), _cell_column(matches))
        elif _is_cellstr(s) and s.dims[1] == 1:
            parts = [_split_text(t, pattern) for t in s]
            counts = {len(p) for p, _ in parts}
            if len(counts) > 1:
                raise MatlabError("Element " "counts of the split pieces "
                                  "differ; split needs the same number of "
                                  "pieces from every string.")
            out = (Cell.from_grid([p for p, _ in parts]),
                   Cell.from_grid([m for _, m in parts]))
        else:
            raise MatlabError("split: Evans supports a character vector or "
                              "a column cell of character vectors.")
        return out if max(nargout, 1) >= 2 else out[0]

    def f_join(self, c, delimiter=" ", dim=None):
        if isinstance(c, str):
            return c
        if not _is_cellstr(c):
            raise MatlabError("First argument must be a cell array of "
                              "character vectors.")
        if not isinstance(delimiter, str):
            raise MatlabError("join: Evans supports only a character vector "
                              "delimiter.")
        r, k = c.dims
        if dim is None:
            dim = 2 if k > 1 else 1
        dim = int(_mr._scalar_of(dim))
        grid = c.grid()
        if dim == 2:
            rows = [delimiter.join(row) for row in grid]
            return rows[0] if len(rows) == 1 else _cell_column(rows)
        if dim == 1:
            cols = [delimiter.join(grid[i][j] for i in range(r))
                    for j in range(k)]
            return cols[0] if len(cols) == 1 else _cell_row(cols)
        raise MatlabError("join: the dimension must be 1 or 2.")

    def f_pad(self, s, *args):
        width, side, fill = None, "right", " "
        rest = list(args)
        if rest and not isinstance(rest[0], str):
            width = int(_mr._scalar_of(rest.pop(0)))
        if rest:
            side = str(rest.pop(0)).lower()
            if side not in ("left", "right", "both"):
                raise MatlabError("Side must be 'left', 'right', or 'both'.")
        if rest:
            fill = rest.pop(0)
            if not isinstance(fill, str) or len(fill) != 1:
                raise MatlabError("Pad character must be a single "
                                  "character.")
        if rest:
            raise MatlabError("Too many input arguments.")
        texts = _texts(s, "pad")
        if width is None:
            width = max((len(t) for t in texts), default=0)

        def one(t: str) -> str:
            extra = max(width - len(t), 0)
            if side == "left":
                return fill * extra + t
            if side == "right":
                return t + fill * extra
            return fill * (extra // 2) + t + fill * (extra - extra // 2)

        return _map(s, one, "pad")

    # ── searching ──────────────────────────────────────────────

    def f_contains(self, s, pattern, *args):
        return _search(s, pattern, args, "contains", lambda t, p: p in t)

    def f_startsWith(self, s, pattern, *args):
        return _search(s, pattern, args, "startsWith", str.startswith)

    def f_endsWith(self, s, pattern, *args):
        return _search(s, pattern, args, "endsWith", str.endswith)

    def f_strfind(self, s, pattern, *args):
        opts = _name_value(args, "strfind", {"forcecelloutput": False})
        if not isinstance(pattern, str):
            raise MatlabError("strfind: the pattern must be a character "
                              "vector.")

        def starts(t: str):
            if not pattern:
                return np.zeros(0)
            return _normalise(_row(i + 1 for i in range(len(t))
                                   if t.startswith(pattern, i)))

        if isinstance(s, str) and _truth(opts["forcecelloutput"]):
            return Cell([starts(s)])
        if not (isinstance(s, str) or _is_cellstr(s)):
            raise MatlabError("First argument must be a character vector or "
                              "a cell array of character vectors.")
        return _map(s, starts, "strfind")

    def _strn(self, a, b, n, fold: bool):
        n = int(_mr._scalar_of(n))

        def eq(x, y) -> bool:
            if not (isinstance(x, str) and isinstance(y, str)) or n <= 0:
                return False
            if fold:
                x, y = x.lower(), y.lower()
            return x[:n] == y[:n]

        if isinstance(a, Cell) and isinstance(b, Cell):
            if len(a) == 1:
                a, b = b, a
            if len(b) == 1:
                return _logical_shaped(a, [eq(x, b[0]) for x in a])
            if a.dims != b.dims:
                raise MatlabError("Inputs must be the same size or either "
                                  "one can be a scalar.")
            return _logical_shaped(a, [eq(x, y) for x, y in zip(a, b)])
        if isinstance(b, Cell):
            a, b = b, a
        if isinstance(a, Cell):
            return _logical_shaped(a, [eq(x, b) for x in a])
        return eq(a, b)

    def f_strncmp(self, a, b, n):
        return self._strn(a, b, n, False)

    def f_strncmpi(self, a, b, n):
        return self._strn(a, b, n, True)

    # ── character classes ──────────────────────────────────────

    def f_isspace(self, s):
        if not isinstance(s, str):
            return _normalise(np.zeros(_mr._shape(s), dtype=bool))
        return _normalise(_bool_row(c.isspace() for c in s))

    def f_isletter(self, s):
        if not isinstance(s, str):
            return _normalise(np.zeros(_mr._shape(s), dtype=bool))
        return _normalise(_bool_row(c.isalpha() for c in s))

    def f_isstrprop(self, s, category, *args):
        opts = _name_value(args, "isstrprop", {"forcecelloutput": False})
        test = _STRPROP.get(str(category).lower())
        if test is None:
            raise MatlabError(f"'{category}' is not a category of "
                              "isstrprop.")

        def one(t):
            if isinstance(t, str):
                return _normalise(_bool_row(test(c) for c in t))
            return _normalise(np.zeros(_mr._shape(t), dtype=bool))

        if isinstance(s, Cell):
            return Cell([one(t) for t in s], rows=s.rows)
        out = one(s)
        return Cell([out]) if _truth(opts["forcecelloutput"]) else out

    # ── regular expressions ────────────────────────────────────

    @_nargout
    def f_regexp(self, s, expr, *options, nargout=1):
        return self._regexp(s, expr, options, nargout, "regexp", False)

    @_nargout
    def f_regexpi(self, s, expr, *options, nargout=1):
        return self._regexp(s, expr, options, nargout, "regexpi", True)

    def _regexp(self, s, expr, options, nargout, fname, fold):
        flags, chosen = _regex_options(options, fname, fold)
        n = max(nargout, 1)
        order = chosen + [k for k in _REGEX_OUTPUTS if k not in chosen]
        if n > len(_REGEX_OUTPUTS):
            raise MatlabError("Too many output arguments.")
        wanted = order[:n]

        def one(t: str, e: str) -> list:
            if not isinstance(t, str):
                raise MatlabError(f"The first input of {fname} must be a "
                                  "character vector or a cell array of "
                                  "character vectors.")
            outs = _regexp_outputs(_compile(e, flags, fname), t, flags)
            return [outs[k] for k in wanted]

        if isinstance(s, str) and isinstance(expr, str):
            results = one(s, expr)
            if flags["forcecelloutput"]:
                results = [Cell([r]) for r in results]
        else:
            if isinstance(s, Cell) and isinstance(expr, Cell):
                if len(expr) == 1:
                    pairs, shape = [(t, expr[0]) for t in s], s
                elif len(s) == 1:
                    pairs, shape = [(s[0], e) for e in expr], expr
                elif s.dims == expr.dims:
                    pairs, shape = list(zip(s, expr)), s
                else:
                    raise MatlabError(f"{fname}: the cell arrays of text "
                                      "and expressions must be the same "
                                      "size.")
            elif isinstance(s, Cell):
                pairs, shape = [(t, expr) for t in s], s
            elif isinstance(expr, Cell):
                pairs, shape = [(s, e) for e in expr], expr
            else:
                raise MatlabError(f"The first input of {fname} must be a "
                                  "character vector or a cell array of "
                                  "character vectors.")
            per = [one(t, e) for t, e in pairs]
            results = [Cell([p[k] for p in per], rows=shape.rows)
                       for k in range(n)]
        return tuple(results) if nargout > 1 else results[0]

    def f_regexprep(self, s, expr, replace, *options):
        once, nth = False, None
        flags = {"ignorecase": False, "emptymatch": False, "dotall": True,
                 "lineanchors": False, "freespacing": False}
        for opt in options:
            if not isinstance(opt, str):
                nth = int(_mr._scalar_of(opt))
                continue
            key = opt.lower()
            if key == "once":
                once = True
            elif key == "matchcase":
                flags["ignorecase"] = False
            elif key == "noemptymatch":
                flags["emptymatch"] = False
            elif key == "dotexceptnewline":
                flags["dotall"] = False
            elif key == "stringanchors":
                flags["lineanchors"] = False
            elif key == "literalspacing":
                flags["freespacing"] = False
            elif key in ("ignorecase", "emptymatch", "dotall",
                         "lineanchors", "freespacing"):
                flags[key] = True
            elif key == "warnings":
                pass
            elif key == "preservecase":
                raise MatlabError("regexprep: Evans does not support "
                                  "'preservecase'.")
            else:
                raise MatlabError(f"'{opt}' is not an option of regexprep.")
        exprs = _texts(expr, "regexprep", "The expression")
        reps = _texts(replace, "regexprep", "The replacement")
        if len(reps) == 1:
            reps = reps * len(exprs)
        elif len(reps) != len(exprs):
            raise MatlabError("regexprep: give one replacement, or one for "
                              "each expression.")
        patterns = [_compile(e, flags, "regexprep") for e in exprs]

        def one(t: str) -> str:
            for pattern, rep in zip(patterns, reps):
                count = [0]

                def sub(m, rep=rep, count=count):
                    if m.end() == m.start() and not flags["emptymatch"]:
                        return m.group(0)
                    count[0] += 1
                    if (once and count[0] > 1) or \
                            (nth is not None and count[0] != nth):
                        return m.group(0)
                    return _replacement(m, rep)

                t = pattern.sub(sub, t)
            return t

        if not (isinstance(s, str) or _is_cellstr(s)):
            raise MatlabError("The first input of regexprep must be a "
                              "character vector or a cell array of character "
                              "vectors.")
        return _map(s, one, "regexprep")
