"""
The language itself.
====================
``eval`` and ``feval``, function handles as text, ``nargin(fn)``,
``validateattributes``, ``containers.Map``, and the two small basics that
colleagues' scripts lean on, ``magic`` and ``fileread``.

A mixin of :class:`.matlab_runtime._Library`: each ``f_<name>`` method is
the MATLAB function ``<name>``. Import :mod:`.matlab_runtime` first, never
this module on its own: the two import each other.
"""

from __future__ import annotations

import inspect
import re
import sys

import numpy as np

from . import matlab_runtime as _mr  # noqa: F401
from .matlab_runtime import (
    Cell,
    MapObject,
    MatlabError,
    _as_array,
    _as_text,
    _is_function,
    _is_number,
    _nargout,
)


def _caller_frame():
    """
    The frame of the MATLAB code that called a library function: the first
    one up the stack whose code was translated (its file name is ``<...>``,
    like ``<console>`` or ``<model.m>``) rather than Evans' own.
    """
    frame = sys._getframe(2)
    while frame is not None and not frame.f_code.co_filename.startswith("<"):
        frame = frame.f_back
    return frame


def _magic(n: int) -> np.ndarray:
    """MATLAB's ``magic(n)``, built the way ``magic.m`` builds it."""
    if n < 1:
        return np.zeros((0, 0))
    if n == 1:
        return np.ones((1, 1))
    if n == 2:
        return np.array([[4.0, 3.0], [1.0, 2.0]])
    if n % 2 == 1:
        k = np.arange(n * n)
        shift = k // n
        c = (np.arange(1, n * n + 1) - shift + (n - 3) // 2) % n
        r = (np.arange(n * n, 0, -1) + 2 * shift) % n
        m = np.zeros(n * n)
        m[c * n + r] = np.arange(1, n * n + 1)
        return m.reshape((n, n), order="F")
    if n % 4 == 0:
        i, j = np.meshgrid(np.arange(1, n + 1), np.arange(1, n + 1),
                           indexing="ij")
        keep = (i % 4) // 2 == (j % 4) // 2
        m = np.arange(1, n * n + 1, dtype=float).reshape((n, n), order="F").T
        m[keep] = n * n + 1 - m[keep]
        return m
    p = n // 2
    a = _magic(p)
    m = np.block([[a, a + 2 * p * p], [a + 3 * p * p, a + p * p]])
    i = np.arange(p)
    k = (n - 2) // 4
    j = np.r_[np.arange(k), np.arange(n - k + 1, n)]
    rows = np.r_[i, i + p]
    swap = np.r_[i + p, i]
    m[np.ix_(rows, j)] = m[np.ix_(swap, j)]
    i = k
    j = [0, i]
    rows = [i, i + p]
    swap = [i + p, i]
    m[np.ix_(rows, j)] = m[np.ix_(swap, j)]
    return m


_CLASSES = {
    "numeric": lambda x: _is_number(x) and not isinstance(x, bool)
    or (isinstance(x, np.ndarray) and x.dtype != bool),
    "double": lambda x: _is_number(x) and not isinstance(x, bool)
    or (isinstance(x, np.ndarray) and x.dtype != bool),
    "single": lambda x: False,
    "float": lambda x: _is_number(x) and not isinstance(x, bool),
    "char": lambda x: isinstance(x, str),
    "string": lambda x: isinstance(x, str),
    "logical": lambda x: isinstance(x, (bool, np.bool_))
    or (isinstance(x, np.ndarray) and x.dtype == bool),
    "cell": lambda x: isinstance(x, Cell),
    "struct": lambda x: isinstance(x, dict),
    "function_handle": _is_function,
}


class _Containers:
    """The ``containers`` package. Only ``containers.Map`` is in it."""

    def __getattr__(self, name):
        raise MatlabError(f"containers.{name} isn't supported in Evans; "
                          f"only containers.Map is.")


def _sorted_values(x) -> list:
    return [_mr._scalar(v) for v in _as_array(x).reshape(-1, order="F")]


class LanguageLibrary:
    """Mixed into ``_Library``."""

    f_containers = _Containers()

    # ── eval and friends ────────────────────────────────────────

    def _translate(self, text, what: str):
        from .matlab import MatlabSyntaxError, translate
        try:
            return translate(_as_text(text))
        except MatlabSyntaxError as exc:
            raise MatlabError(f"Invalid {what}. {exc.message}") from None

    def _run_text(self, text, glob: dict, scope: dict, nargout: int):
        """Run MATLAB text in ``scope``; with ``nargout``, return its value."""
        self.rt.ns.setdefault("__ml__", self.rt)
        if nargout:
            chunks = self._translate(f"__evans_value__ = ({_as_text(text)});",
                                     "expression")
            for chunk in chunks:
                exec(compile(chunk.python, "<eval>", "exec"), glob, scope)
            return scope.pop("__evans_value__")
        for chunk in self._translate(text, "expression"):
            exec(compile(chunk.python, "<eval>", "exec"), glob, scope)
        return None

    @_nargout
    def f_eval(self, text, catch=None, nargout=0):
        if not isinstance(text, str):
            raise MatlabError("The first input to eval must be a character "
                              "vector.")
        frame = _caller_frame()
        if frame is None or frame.f_locals is frame.f_globals:
            glob = scope = self.rt.ns
            check = None
        else:
            glob, scope = frame.f_globals, dict(frame.f_locals)
            check = dict(scope)
        try:
            value = self._run_text(text, glob, scope, nargout)
        except Exception:                                  # noqa: BLE001
            if catch is None:
                raise
            return self._run_text(catch, glob, scope, nargout)
        if check is not None and any(
                k not in check or scope[k] is not check[k] for k in scope):
            raise MatlabError(
                "eval inside a function can read its variables but not "
                "set them in Evans; return the value instead, or use "
                "assignin-free code.")
        return value

    @_nargout
    def f_evalin(self, workspace, text, catch=None, nargout=0):
        where = _as_text(workspace).lower()
        if where != "base":
            raise MatlabError("evalin supports only the 'base' workspace "
                              "in Evans.")
        scope = self.rt.ns
        try:
            return self._run_text(text, scope, scope, nargout)
        except Exception:                                  # noqa: BLE001
            if catch is None:
                raise
            return self._run_text(catch, scope, scope, nargout)

    def _resolve_function(self, f, who: str):
        if isinstance(f, str):
            return self.rt.lookup(f, self.rt.ns, self.rt.ns)
        if _is_function(f):
            return f
        raise MatlabError(f"The first input to {who} must be a function "
                          f"handle or the name of a function.")

    @_nargout
    def f_feval(self, f, *args, nargout=1):
        fn = self._resolve_function(f, "feval")
        return self.rt.call(fn, args, nargout=nargout)

    def f_str2func(self, text):
        text = _as_text(text).strip()
        if text.startswith("@"):
            return self.rt.evaluate(text)
        if not re.fullmatch(r"[A-Za-z]\w*", text):
            raise MatlabError("The input must be a function name or an "
                              "anonymous function.")
        return self.rt.lookup(text, self.rt.ns, self.rt.ns)

    def f_func2str(self, f):
        if not _is_function(f):
            raise MatlabError("The input must be a function handle.")
        text = getattr(f, "_ml_text", None)
        if text:
            return text
        for name in sorted(self.names):
            if getattr(self, "f_" + name, None) == f:
                return name
        for name, value in self.rt.base.items():
            if value is f:
                return name
        name = getattr(f, "__name__", "") or type(f).__name__
        return name[2:] if name.startswith("f_") else name

    def f_nargin(self, f):
        fn = self._resolve_function(f, "nargin")
        text = getattr(fn, "_ml_text", None)
        if text:
            params = re.match(r"@\(([^)]*)\)", text).group(1)
            names = [p.strip() for p in params.split(",") if p.strip()]
            if names and names[-1] == "varargin":
                return -len(names)
            return len(names)
        try:
            sig = inspect.signature(fn)
        except (TypeError, ValueError):
            raise MatlabError("nargin can't tell how many inputs this "
                              "function takes.") from None
        count, var = 0, False
        for p in sig.parameters.values():
            if p.kind == p.VAR_POSITIONAL:
                var = True
            elif p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD):
                count += 1
        return -(count + 1) if var else count

    # ── validateattributes ──────────────────────────────────────

    def f_validateattributes(self, a, classes, attributes, *more):
        classes = [_as_text(c) for c in (classes if isinstance(classes, Cell)
                                         else [classes])]
        attrs = list(attributes) if isinstance(attributes, Cell) else \
            [attributes]
        name = "input"
        for extra in more:
            if isinstance(extra, str):
                name = extra          # funcName, then varName: take varName
        if len(more) >= 2 and isinstance(more[1], str):
            name = more[1]
        if classes and not any(_CLASSES.get(c, lambda x: False)(a)
                               for c in classes):
            raise MatlabError(
                f"Expected {name} to be one of these types:\n\n  "
                f"{', '.join(classes)}\n\nInstead its type was "
                f"{self.f_class(a)}.")
        arr = None if isinstance(a, (str, Cell, dict)) or _is_function(a) \
            else _as_array(a)
        k = 0
        while k < len(attrs):
            attr = _as_text(attrs[k]).lower()
            k += 1
            if attr in ("<", "<=", ">", ">=", "numel", "size", "ncols",
                        "nrows", "ndims", "numel"):
                limit = attrs[k]
                k += 1
                self._check_limit(name, a, arr, attr, limit)
                continue
            self._check_attr(name, a, arr, attr)
        return None

    @staticmethod
    def _fail(name: str, what: str):
        raise MatlabError(f"Expected {name} to be {what}.")

    def _check_limit(self, name, a, arr, attr, limit):
        lim = _mr._scalar(_as_array(limit).reshape(-1)[0]) \
            if not isinstance(limit, (int, float)) else limit
        if attr in ("<", "<=", ">", ">="):
            ok = {"<": np.all(arr < lim), "<=": np.all(arr <= lim),
                  ">": np.all(arr > lim), ">=": np.all(arr >= lim)}[attr]
            word = {"<": "less than", "<=": "less than or equal to",
                    ">": "greater than", ">=": "greater than or equal to"}
            if not ok:
                self._fail(name, f"{word[attr]} {_mr._number(lim)}")
        elif attr == "numel":
            if _mr._numel(a) != lim:
                self._fail(name, f"an array with {int(lim)} elements")
        elif attr == "size":
            want = _as_array(limit).reshape(-1)
            have = _mr._shape(a)
            if any(not np.isnan(w) and w != h for w, h in zip(want, have)):
                self._fail(name, "an array of the size "
                           + "x".join(str(int(w)) for w in want))
        elif attr == "nrows":
            if _mr._shape(a)[0] != lim:
                self._fail(name, f"an array with {int(lim)} rows")
        elif attr == "ncols":
            if _mr._shape(a)[1] != lim:
                self._fail(name, f"an array with {int(lim)} columns")

    def _check_attr(self, name, a, arr, attr):
        r, c = _mr._shape(a)
        simple = {
            "scalar": r * c == 1,
            "vector": (r == 1 or c == 1) and r * c >= 1,
            "row": r == 1,
            "column": c == 1,
            "2d": True,
            "nonempty": r * c > 0,
            "square": r == c,
        }
        if attr in simple:
            if not simple[attr]:
                self._fail(name, {"scalar": "scalar",
                                  "vector": "a vector",
                                  "row": "a row vector",
                                  "column": "a column vector",
                                  "nonempty": "nonempty",
                                  "square": "a square matrix"}[attr])
            return
        if arr is None:
            raise MatlabError(f"Expected {name} to be numeric to check "
                              f"'{attr}'.")
        tests = {
            "positive": lambda v: np.all(v > 0),
            "nonnegative": lambda v: np.all(v >= 0),
            "negative": lambda v: np.all(v < 0),
            "nonpositive": lambda v: np.all(v <= 0),
            "nonzero": lambda v: np.all(v != 0),
            "nonnan": lambda v: not np.any(np.isnan(v)),
            "finite": lambda v: np.all(np.isfinite(v)),
            "real": lambda v: not np.iscomplexobj(v),
            "integer": lambda v: np.all(np.mod(np.real(v), 1) == 0),
            "binary": lambda v: np.all((v == 0) | (v == 1)),
            "even": lambda v: np.all(np.mod(v, 2) == 0),
            "odd": lambda v: np.all(np.mod(v, 2) == 1),
            "increasing": lambda v: np.all(np.diff(v.reshape(-1)) > 0),
            "decreasing": lambda v: np.all(np.diff(v.reshape(-1)) < 0),
            "nondecreasing": lambda v: np.all(np.diff(v.reshape(-1)) >= 0),
            "nonincreasing": lambda v: np.all(np.diff(v.reshape(-1)) <= 0),
        }
        if attr not in tests:
            raise MatlabError(f"Unknown attribute '{attr}'.")
        if not tests[attr](arr):
            self._fail(name, attr)

    # ── magic and fileread ──────────────────────────────────────

    def f_magic(self, n):
        if not _is_number(n) or n != int(n):
            raise MatlabError("magic: N must be a scalar integer.")
        out = _magic(int(n))
        return _mr._normalise(out) if out.size > 1 else \
            (_mr._scalar(out.reshape(-1)[0]) if out.size else out)

    def f_fileread(self, filename):
        path = self.rt.resolve(filename)
        try:
            with open(path, "rb") as fh:
                raw = fh.read()
        except OSError:
            raise MatlabError(f"Unable to open file '{_as_text(filename)}' "
                              f"for reading.") from None
        try:
            return raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            return raw.decode("cp1252", errors="replace")

    # ── containers.Map ──────────────────────────────────────────

    def f_containers_Map(self, *args):         # noqa: N802
        options = {"keytype": None, "valuetype": None, "uniformvalues": True}
        rest = list(args)
        positional = []
        if rest and not (isinstance(rest[0], str)
                         and rest[0].lower() in options):
            positional = rest[:2]
            rest = rest[2:]
        while rest:
            if len(rest) < 2 or not (isinstance(rest[0], str)
                                     and rest[0].lower() in options):
                raise MatlabError("Map: expected name-value pairs "
                                  "'KeyType', 'ValueType' or "
                                  "'UniformValues'.")
            options[rest[0].lower()] = rest[1]
            del rest[:2]
        if not positional:
            key_type = options["keytype"] or "char"
            if key_type != "char" and key_type not in MapObject._NUMERIC:
                raise MatlabError(f"Map: '{key_type}' is not a valid "
                                  f"KeyType.")
            return MapObject(key_type, options["valuetype"] or "any")
        if len(positional) != 2:
            raise MatlabError("Map: keys and values must be given "
                              "together.")
        keys, values = positional
        if isinstance(keys, Cell):
            key_list = list(keys)
            if not isinstance(values, Cell):
                if len(key_list) == 1:
                    values = Cell([values])
                elif _mr._numel(values) == len(key_list):
                    values = Cell(_sorted_values(values))
                else:
                    raise MatlabError("Map: the number of keys and values "
                                      "must match.")
            value_list = list(values)
        elif isinstance(keys, str) or _is_number(keys):
            key_list, value_list = [keys], [values]
        else:
            key_list = _sorted_values(keys)
            if not isinstance(values, Cell):
                values = Cell([values]) if len(key_list) == 1 else values
            value_list = list(values) if isinstance(values, Cell) else \
                _sorted_values(values)
        if len(key_list) != len(value_list):
            raise MatlabError("Map: the number of keys and values must "
                              "match.")
        if not key_list:
            return MapObject("char", "any")
        text = all(isinstance(k, str) for k in key_list)
        if not text and not all(_is_number(k) and not isinstance(k, bool)
                                for k in key_list):
            raise MatlabError("Map: all keys must be text, or all must be "
                              "real numbers.")
        key_type = "char" if text else (options["keytype"] or "double")
        if options["valuetype"]:
            value_type = options["valuetype"]
        elif options["uniformvalues"] is not False and value_list \
                and all(isinstance(v, str) for v in value_list):
            value_type = "char"
        elif options["uniformvalues"] is not False and value_list \
                and all(_is_number(v) and not isinstance(v, bool)
                        for v in value_list):
            value_type = "double"
        else:
            value_type = "any"
        out = MapObject(key_type, value_type)
        for k, v in zip(key_list, value_list):
            out.put(k, _mr.share(v))
        return out

    @staticmethod
    def _as_map(m, who: str) -> MapObject:
        if not isinstance(m, MapObject):
            raise MatlabError(f"{who}: the input must be a containers.Map.")
        return m

    def f_isKey(self, m, k):                   # noqa: N802
        return self._as_map(m, "isKey").isKey(k)

    def f_keys(self, m):
        return self._as_map(m, "keys").keys()

    def f_values(self, m, which=None):
        return self._as_map(m, "values").values(which)

    def f_remove(self, m, k):
        return self._as_map(m, "remove").remove(k)


def _operator(name: str):
    def call(self, *args):
        return getattr(self.rt, name)(*args)
    call.__name__ = "f_" + name
    return call


# ``plus(a, b)`` and the rest, so ``@plus`` and ``feval('minus', ...)`` work.
for _name in ("plus", "minus", "times", "rdivide", "ldivide", "mtimes",
              "mrdivide", "mldivide", "power", "mpower", "uminus", "uplus",
              "eq", "ne", "lt", "le", "gt", "ge", "transpose", "ctranspose"):
    setattr(LanguageLibrary, "f_" + _name, _operator(_name))
