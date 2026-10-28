"""
Workspace, files and number helpers.
====================================
``who``, ``dir``, ``system``, dates, and integer and special functions.

A mixin of :class:`.matlab_runtime._Library`: each ``f_<name>`` method is
the MATLAB function ``<name>``. It is imported by :mod:`.matlab_runtime`
just before ``_Library`` is defined, so the helpers above that line can be
imported from it by name; anything defined further down is reached through
the module (``_mr._sprintf``) at call time. Import :mod:`.matlab_runtime` first, never this module on
its own: the two import each other.

Which workspace
---------------
``who``, ``whos``, ``exist`` and ``which`` answer for the workspace of the
code that called them: the nearest frame on the stack that runs translated
MATLAB (its globals hold this runtime as ``__ml__``). At the prompt or in a
script that is the base workspace; inside a function file, the function's
own locals.
"""

from __future__ import annotations

import datetime as _dt
import math
import os
import re
import shutil
import subprocess
import sys
import time
import types

import numpy as np

from . import matlab_runtime as _mr  # noqa: F401
from .matlab_runtime import (
    Cell,
    MatlabError,
    Struct,
    StructArray,
    _as_text,
    _float_array,
    _is_function,
    _is_sym,
    _nargout,
    _normalise,
    _shape,
)

#: Seconds between looks at the Stop button while ``pause`` or ``system``
#: waits.
_SLICE = 0.05

_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December")
_DAYS = ("Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
         "Saturday")
_CUMDAYS = np.array([0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334])

#: ``datestr``'s numbered formats.
_DATE_FORMATS = {
    0: "dd-mmm-yyyy HH:MM:SS", 1: "dd-mmm-yyyy", 2: "mm/dd/yy", 3: "mmm",
    4: "m", 5: "mm", 6: "mm/dd", 7: "dd", 8: "ddd", 9: "d", 10: "yyyy",
    11: "yy", 12: "mmmyy", 13: "HH:MM:SS", 14: "HH:MM:SS PM", 15: "HH:MM",
    16: "HH:MM PM", 17: "QQ-YY", 18: "QQ", 19: "dd/mm", 20: "dd/mm/yy",
    21: "mmm.dd,yyyy HH:MM:SS", 22: "mmm.dd,yyyy", 23: "mm/dd/yyyy",
    24: "dd/mm/yyyy", 25: "yy/mm/dd", 26: "yyyy/mm/dd", 27: "QQ-YYYY",
    28: "mmmyyyy", 29: "yyyy-mm-dd", 30: "yyyymmddTHHMMSS",
    31: "yyyy-mm-dd HH:MM:SS",
}

#: What ``datenum(str)`` tries, in order (US month/day first, as MATLAB).
_PARSE_FORMATS = (
    "dd-mmm-yyyy HH:MM:SS", "dd-mmm-yyyy HH:MM", "dd-mmm-yyyy",
    "yyyy-mm-dd HH:MM:SS", "yyyy-mm-dd HH:MM", "yyyy-mm-ddTHH:MM:SS",
    "yyyy-mm-dd", "yyyy/mm/dd HH:MM:SS", "yyyy/mm/dd",
    "mm/dd/yyyy HH:MM:SS", "mm/dd/yyyy", "mm/dd/yy", "mm/dd",
    "mmm.dd,yyyy HH:MM:SS", "mmm.dd,yyyy", "mmm dd yyyy", "dd mmm yyyy",
    "yyyymmddTHHMMSS", "HH:MM:SS PM", "HH:MM PM", "HH:MM:SS", "HH:MM",
)

_DATE_TOKENS = ("yyyy", "YYYY", "mmmm", "mmm", "dddd", "ddd", "FFF", "yy",
                "YY", "mm", "dd", "HH", "MM", "SS", "AM", "PM", "QQ", "m",
                "d")


class SystemLibrary:
    """who, dir, datestr, nchoosek and the rest."""

    # ── whose workspace ─────────────────────────────────────────

    def _caller_scope(self) -> tuple[dict, bool]:
        """
        The variables of the MATLAB code that called us, and whether that
        code is a function (its locals) rather than the workspace.
        """
        frame = sys._getframe(1)
        while frame is not None:
            if frame.f_globals.get("__ml__") is self.rt:
                inside = frame.f_code.co_name != "<module>"
                return dict(frame.f_locals), inside
            frame = frame.f_back
        return self.rt.ns, False

    def _variables(self) -> dict:
        """The user's variables, as ``who`` lists them."""
        scope, inside = self._caller_scope()
        base = self.rt.base
        out = {}
        for name, value in scope.items():
            if name.startswith("_") or value is None \
                    or isinstance(value, types.ModuleType) \
                    or value is base.get(name, object()) \
                    or getattr(value, "_ml_function", False) \
                    or (not inside and name in self.rt.script_functions):
                continue
            if inside and name in ("nargin", "nargout"):
                continue
            out[name] = value
        return out

    def _selected(self, args) -> tuple[dict, bool]:
        """``who``/``whos`` arguments: name patterns, ``global``."""
        names = [_as_text(a) for a in args]
        for n in names:
            if n.lower() in ("-file", "-regexp"):
                raise MatlabError(f"who/whos {n} isn't supported in Evans; "
                                  f"list the workspace instead.")
        is_global = bool(names) and names[0].lower() == "global"
        if is_global:
            names = names[1:]
            pool = dict(self.rt.global_vars)
        else:
            pool = self._variables()
        if names:
            pats = [re.compile(_wild(n)) for n in names]
            pool = {k: v for k, v in pool.items()
                    if any(p.fullmatch(k) for p in pats)}
        return dict(sorted(pool.items())), is_global

    # ── who, whos, which, exist ─────────────────────────────────

    @_nargout
    def f_who(self, *args, nargout=0):
        pool, is_global = self._selected(args)
        names = list(pool)
        if nargout:
            return Cell(names, rows=len(names)) if names else Cell()
        if names:
            kind = "global variables" if is_global else "variables"
            print(f"\nYour {kind} are:\n")
            print("\n".join(_columns(names)) + "\n")
        return None

    @_nargout
    def f_whos(self, *args, nargout=0):
        pool, is_global = self._selected(args)
        globals_ = set(self.rt.global_vars) if is_global \
            else self.rt._workspace_globals
        rows = []
        for name, value in pool.items():
            r, c = _value_shape(value)
            rows.append(dict(name=name, size=(r, c), bytes=_bytes(value),
                             cls=_class_of(self, value),
                             complex=_is_complex(value),
                             glob=name in globals_))
        if nargout:
            items = [Struct(name=d["name"],
                            size=np.array([float(d["size"][0]),
                                           float(d["size"][1])]),
                            bytes=d["bytes"], **{"class": d["cls"]},
                            **{"global": d["glob"]}, sparse=False,
                            complex=d["complex"],
                            nesting=Struct(function="", level=1),
                            persistent=False)
                     for d in rows]
            return StructArray(items, rows=len(items))
        if not rows:
            return None
        nw = max(4, *(len(d["name"]) for d in rows)) + 6
        sizes = [f"{d['size'][0]}x{d['size'][1]}" for d in rows]
        sw = max(16, *(len(s) + 4 for s in sizes))
        bw = max(5, *(len(str(d["bytes"])) for d in rows))
        cw = max(10, *(len(d["cls"]) + 2 for d in rows))
        lines = ["  " + "Name".ljust(nw) + "Size".ljust(sw)
                 + "Bytes".rjust(bw) + "  " + "Class".ljust(cw)
                 + "Attributes", ""]
        for d, size in zip(rows, sizes):
            attrs = ", ".join(a for a, on in (("complex", d["complex"]),
                                               ("global", d["glob"])) if on)
            lines.append(("  " + d["name"].ljust(nw) + size.ljust(sw)
                          + str(d["bytes"]).rjust(bw) + "  "
                          + d["cls"].ljust(cw) + attrs).rstrip())
        print("\n".join(lines) + "\n")
        return None

    @_nargout
    def f_which(self, *args, nargout=0):
        names = [_as_text(a) for a in args]
        if any(n.lower() == "-all" for n in names):
            raise MatlabError("which -all isn't supported in Evans: it "
                              "names only the function a call would run.")
        if len(names) != 1:
            raise MatlabError("which needs one name: which name")
        name = names[0]
        scope, _ = self._caller_scope()
        found, text = "", ""
        if name in self._variables():
            found, text = "variable", f"{name} is a variable."
        elif name in self.rt.script_functions and _is_function(
                scope.get(name, self.rt.ns.get(name))):
            found = f"{name} (local function)"
            text = f"{name} is a local function of the running script."
        else:
            path = self.rt.find_file(name, refresh=True)
            if path is None and name.endswith(".m"):
                path = self.rt.find_file(name[:-2], refresh=True)
            if path is None and _is_builtin(self, name):
                found = text = "built-in (Evans)"
            elif path is None:
                path = _on_path(self.rt, name)
            if path is not None:
                found = text = path
        if nargout:
            return found
        print(text or f"'{name}' not found.")
        return None

    def f_exist(self, name, kind=None):
        if not isinstance(name, str):
            raise MatlabError("The first input to exist must be a string "
                              "scalar or character vector.")
        kind = None if kind is None else _as_text(kind).lower()
        if kind not in (None, "var", "file", "dir", "builtin", "class"):
            raise MatlabError("Invalid search type. Search type must be "
                              "'var', 'builtin', 'class', 'dir', or 'file'.")
        if kind == "class":
            raise MatlabError("exist(name, 'class') isn't supported in "
                              "Evans: it has no MATLAB classes.")
        if kind in (None, "var") and name in self._variables():
            return 1
        if kind == "var":
            return 0
        if kind in (None, "file"):
            if self.rt.find_file(name, refresh=True) is not None \
                    or os.path.isfile(self.rt.resolve(name)) \
                    or _on_path(self.rt, name) is not None:
                return 2
            if os.path.isdir(self.rt.resolve(name)):
                return 7
        if kind == "dir":
            return 7 if os.path.isdir(self.rt.resolve(name)) else 0
        if kind in (None, "builtin") and _is_builtin(self, name):
            return 5
        return 0

    # ── files and folders ───────────────────────────────────────

    @_nargout
    def f_dir(self, pattern=None, nargout=0):
        entries = self._dir_entries(pattern)
        if nargout:
            items = [_dir_struct(*e) for e in entries]
            return StructArray(items, rows=len(items))
        if entries:
            print("\n" + "\n".join(_columns([e[0] for e in entries]))
                  + "\n")
        elif pattern is not None:
            print("Warning: Folder or file not found.")
        return None

    @_nargout
    def f_ls(self, pattern=None, nargout=0):
        if nargout:
            raise MatlabError("x = ls isn't supported in Evans (MATLAB "
                              "returns a char matrix); use d = dir and "
                              "{d.name}.")
        return self.f_dir(pattern, nargout=0)

    def _dir_entries(self, pattern) -> list[tuple[str, str, str]]:
        """``(name, folder, full path)`` for each match, sorted by name."""
        rt = self.rt
        if pattern is None:
            return _folder_listing(rt.folder)
        pattern = _as_text(pattern)
        full = rt.resolve(pattern)
        if "**" in pattern:
            head, _, tail = full.partition("**")
            tail = tail.lstrip("\\/") or "*"
            rx = re.compile(_wild(tail), _CASE)
            base = head.rstrip("\\/") or os.sep
            out = []
            for folder, dirs, files in os.walk(base):
                dirs.sort()
                out += [(n, folder, os.path.join(folder, n))
                        for n in sorted(dirs + files) if rx.fullmatch(n)]
            return out
        if os.path.isdir(full):
            return _folder_listing(full)
        folder, base = os.path.split(full)
        if "*" in base:
            return [e for e in _folder_listing(folder, dots=False)
                    if re.fullmatch(_wild(base), e[0], _CASE)]
        if os.path.exists(full):
            return [(base, folder, full)]
        return []

    def _expand(self, name) -> list[str]:
        """A file name, wildcards in its last part expanded."""
        full = self.rt.resolve(name)
        folder, base = os.path.split(full)
        if "*" in base:
            return [e[2] for e in _folder_listing(folder, dots=False)
                    if re.fullmatch(_wild(base), e[0], _CASE)]
        return [full] if os.path.exists(full) else []

    def f_delete(self, *names):
        for name in names:
            if not isinstance(name, str):
                raise MatlabError("delete(h) of graphics objects isn't "
                                  "supported in Evans; delete takes file "
                                  "names.")
            full = self.rt.resolve(name)
            if "*" not in os.path.basename(full) and os.path.isdir(full):
                raise MatlabError(f"'{name}' is a folder; delete removes "
                                  f"files. Use rmdir to remove a folder.")
            targets = [t for t in self._expand(name) if os.path.isfile(t)]
            if not targets:
                print(f"Warning: File '{name}' not found.")
            for target in targets:
                os.remove(target)
        return None

    @_nargout
    def f_copyfile(self, src, dst=None, *flags, nargout=0):
        return _status(lambda: self._transfer(src, dst, move=False),
                       nargout, "MATLAB:COPYFILE:")

    @_nargout
    def f_movefile(self, src, dst=None, *flags, nargout=0):
        return _status(lambda: self._transfer(src, dst, move=True),
                       nargout, "MATLAB:MOVEFILE:")

    def _transfer(self, src, dst, move: bool) -> None:
        sources = self._expand(_as_text(src))
        if not sources:
            raise MatlabError("No matching files were found.")
        target = self.rt.resolve("." if dst is None else dst)
        many = len(sources) > 1 or "*" in os.path.basename(_as_text(src))
        if many and not os.path.isdir(target):
            os.makedirs(target)
        for source in sources:
            if os.path.exists(target) and os.path.samefile(source, target):
                raise MatlabError("Cannot copy or move a file or directory "
                                  "onto itself.")
            into = os.path.isdir(target) and (many or os.path.isfile(source)
                                              or move)
            dest = os.path.join(target, os.path.basename(source)) if into \
                else target
            try:
                if move:
                    shutil.move(source, dest)
                elif os.path.isdir(source):
                    # A folder's contents go into the destination folder.
                    shutil.copytree(source, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(source, dest)
            except OSError as exc:
                raise MatlabError(exc.strerror or str(exc)) from None

    @_nargout
    def f_mkdir(self, *parts, nargout=0):
        if not 1 <= len(parts) <= 2:
            raise MatlabError("mkdir needs mkdir(folder) or "
                              "mkdir(parentFolder, folder).")
        path = self.rt.resolve(os.path.join(*map(_as_text, parts)))
        if os.path.isdir(path):
            message = "Directory already exists."
            if not nargout:
                print(f"Warning: {message}")
                return None
            return _outputs((True, message, "MATLAB:MKDIR:DirectoryExists"),
                            nargout)

        def make():
            try:
                os.makedirs(path)
            except OSError as exc:
                raise MatlabError(f"Cannot create directory {path}: "
                                  f"{exc.strerror or exc}") from None
        return _status(make, nargout, "MATLAB:MKDIR:")

    @_nargout
    def f_rmdir(self, folder, *flags, nargout=0):
        recursive = any(_as_text(f).lower() == "s" for f in flags)
        path = self.rt.resolve(folder)

        def remove():
            if not os.path.isdir(path):
                raise MatlabError(f"No directories were removed: "
                                  f"{_as_text(folder)} is not a folder or "
                                  f"does not exist.")
            if not recursive and os.listdir(path):
                raise MatlabError(f"No directories were removed: "
                                  f"{_as_text(folder)} is not empty. "
                                  f"rmdir(folder, 's') removes it and its "
                                  f"contents.")
            try:
                shutil.rmtree(path) if recursive else os.rmdir(path)
            except OSError as exc:
                raise MatlabError(f"No directories were removed: "
                                  f"{exc.strerror or exc}") from None
        return _status(remove, nargout, "MATLAB:RMDIR:")

    # ── the operating system ────────────────────────────────────

    @_nargout
    def f_system(self, command, *options, nargout=0):
        command = _as_text(command)
        echo = nargout < 2 or any(_as_text(o).lower() == "-echo"
                                  for o in options)
        if command.rstrip().endswith("&"):
            subprocess.Popen(command.rstrip()[:-1], shell=True,
                             cwd=self.rt.folder, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            status, out = 0, ""
        else:
            proc = subprocess.Popen(command, shell=True, cwd=self.rt.folder,
                                    stdin=subprocess.DEVNULL,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
            while True:
                try:
                    raw, _ = proc.communicate(timeout=_SLICE)
                    break
                except subprocess.TimeoutExpired:
                    if _stop_requested(self.rt):
                        proc.kill()
                        proc.communicate()
                        from .tracer import Interrupted
                        raise Interrupted(None) from None
            status, out = proc.returncode, _decode(raw)
        if echo and out:
            print(out, end="" if out.endswith("\n") else "\n")
        return _outputs((status, out), nargout) if nargout else status

    def f_getenv(self, name=None):
        if name is None:
            raise MatlabError("getenv() with no name isn't supported in "
                              "Evans; ask for one variable: getenv('PATH').")
        return os.environ.get(_as_text(name), "")

    def f_setenv(self, name, value=""):
        name, value = _as_text(name), _as_text(value)
        if value:
            os.environ[name] = value
        else:
            os.environ.pop(name, None)

    @_nargout
    def f_computer(self, arch=None, nargout=1):
        if sys.platform.startswith("win"):
            name, short = "PCWIN64", "win64"
        elif sys.platform == "darwin":
            arm = os.uname().machine == "arm64"
            name, short = ("MACA64", "maca64") if arm else ("MACI64",
                                                            "maci64")
        else:
            name, short = "GLNXA64", "glnxa64"
        if arch is not None:
            if _as_text(arch).lower() != "arch":
                raise MatlabError("computer takes only 'arch'.")
            return short
        return _outputs((name, float(2**48 - 1), "L"), nargout) \
            if nargout > 1 else name

    def f_ispc(self):
        return sys.platform.startswith("win")

    def f_isunix(self):
        return not sys.platform.startswith("win")

    def f_ismac(self):
        return sys.platform == "darwin"

    # ── pause ───────────────────────────────────────────────────

    @_nargout
    def f_pause(self, seconds=None, *_, nargout=0):
        """
        ``pause(t)`` waits t seconds, and Stop ends the wait; a bare
        ``pause`` waits for no key; ``pause off`` makes later pauses
        return at once.
        """
        if isinstance(seconds, str):
            state = seconds.lower()
            previous = "on" if getattr(self, "_pause_on", True) else "off"
            if state in ("on", "off"):
                self._pause_on = state == "on"
                return previous if nargout else None
            if state == "query":
                return previous
            raise MatlabError("pause takes a time, 'on', 'off' or 'query'.")
        if seconds is None or not getattr(self, "_pause_on", True):
            return None
        t = float(np.real(_mr._scalar_of(seconds)))
        if not (math.isfinite(t) and t > 0):
            return None
        waiter = _mr._pause_for
        if getattr(waiter, "__module__", None) == _mr.__name__ \
                and getattr(waiter, "__name__", "") == "_pause_for":
            _stoppable_wait(self.rt, t)
        else:
            waiter(t)            # a test's stand-in for the wait
        return None

    # ── dates ───────────────────────────────────────────────────

    def f_clock(self):
        n = _dt.datetime.now()
        return np.array([n.year, n.month, n.day, n.hour, n.minute,
                         n.second + n.microsecond / 1e6], float)

    def f_now(self):
        return float(_datenum_of(*self.f_clock()))

    def f_date(self):
        return _format_date(math.floor(self.f_now()), "dd-mmm-yyyy")

    def f_datenum(self, *args):
        if not args:
            raise MatlabError("datenum needs a date.")
        first = args[0]
        if isinstance(first, (str, Cell)):
            fmt, pivot = None, None
            for extra in args[1:]:
                if isinstance(extra, str):
                    fmt = extra
                else:
                    pivot = int(_mr._scalar_of(extra))
            texts = [first] if isinstance(first, str) else list(first)
            values = [_datenum_of(*_parse_date(_as_text(t), fmt, pivot))
                      for t in texts]
            if isinstance(first, str):
                return float(values[0])
            return np.array(values, float).reshape(-1, 1)
        if len(args) == 1:
            vec = np.atleast_2d(_float_array(first))
            if vec.shape[1] not in (3, 6):
                raise MatlabError("datenum(V) needs a date vector of 3 or 6 "
                                  "columns: [y m d] or [y m d h mi s].")
            out = _datenum_of(*(vec[:, k] for k in range(vec.shape[1])))
            return float(out[0]) if out.size == 1 else out.reshape(-1, 1)
        if len(args) > 6 or len(args) < 3:
            raise MatlabError("datenum needs datenum(y, m, d) or "
                              "datenum(y, m, d, h, mi, s).")
        parts = [_float_array(a) for a in args]
        out = _datenum_of(*parts)
        return _normalise(np.asarray(out, float)) if np.ndim(out) \
            else float(out)

    def f_datevec(self, d, fmt=None):
        if isinstance(d, (str, Cell)):
            texts = [d] if isinstance(d, str) else list(d)
            rows = [_datevec(_datenum_of(*_parse_date(_as_text(t), fmt,
                                                      None))) for t in texts]
        else:
            rows = [_datevec(v) for v in np.asarray(_float_array(d),
                                                    float).reshape(-1)]
        out = np.array(rows, float)
        return out.reshape(-1) if len(rows) == 1 else out

    def f_datestr(self, d, fmt=None, *_):
        if isinstance(d, Cell):
            if len(d) != 1:
                raise MatlabError(_MANY_DATES)
            d = d[0]
        if isinstance(d, str):
            dn = _datenum_of(*_parse_date(d, None, None))
        else:
            a = np.atleast_2d(_float_array(d))
            if _looks_like_datevec(a):
                if a.shape[0] != 1:
                    raise MatlabError(_MANY_DATES)
                dn = _datenum_of(*a[0])
            else:
                if a.size != 1:
                    raise MatlabError(_MANY_DATES)
                dn = float(a.reshape(-1)[0])
        if fmt is None:
            fmt = 0 if dn != math.floor(dn) else 1
        if not isinstance(fmt, str):
            code = int(_mr._scalar_of(fmt))
            if code not in _DATE_FORMATS:
                raise MatlabError(f"datestr format {code} isn't one Evans "
                                  f"knows (0 to 31).")
            fmt = _DATE_FORMATS[code]
        return _format_date(float(dn), fmt)

    # ── integers in other bases ─────────────────────────────────

    def f_dec2bin(self, d, n=None):
        return _to_base(d, 2, n, "dec2bin")

    def f_dec2hex(self, d, n=None):
        return _to_base(d, 16, n, "dec2hex")

    def f_dec2base(self, d, base, n=None):
        if isinstance(base, str):
            raise MatlabError("dec2base with a symbol set isn't supported in "
                              "Evans; give the base as a number, 2 to 36.")
        b = int(_mr._scalar_of(base))
        if not 2 <= b <= 36:
            raise MatlabError("Base must be an integer between 2 and 36.")
        return _to_base(d, b, n, "dec2base")

    def f_bin2dec(self, s):
        return _from_base(s, 2, "Binary string may consist only of "
                                "characters 0 and 1")

    def f_hex2dec(self, s):
        return _from_base(s, 16, "Input string found with characters other "
                                 "than 0-9, a-f, or A-F.")

    def f_base2dec(self, s, base):
        b = int(_mr._scalar_of(base))
        if not 2 <= b <= 36:
            raise MatlabError("Base must be an integer between 2 and 36.")
        return _from_base(s, b, f"String contains characters that are not "
                                f"digits in base {b}.")

    # ── combinatorics and number theory ─────────────────────────

    def f_factorial(self, n):
        a = _real(n, "factorial")
        bad = (np.fix(a) != a) | (a < 0)
        if np.any(bad):
            raise MatlabError("N must be a matrix of non-negative integers.")
        table = np.cumprod(np.r_[1.0, np.arange(1.0, 171.0)])
        out = np.full(a.shape, np.inf)
        small = a <= 170
        out[small] = table[a[small].astype(int)]
        return _shaped(out)

    def f_nchoosek(self, v, k):
        k_ = _mr._scalar_of(k)
        if isinstance(v, (str, Cell)):
            raise MatlabError("nchoosek of a char or cell vector isn't "
                              "supported in Evans (it returns a char or "
                              "cell matrix).")
        a = np.asarray(_float_array(v))
        if not (float(k_) == int(k_) and k_ >= 0):
            raise MatlabError("K must be an integer between 0 and N.")
        k_ = int(k_)
        if a.size == 1:
            n = float(a.reshape(-1)[0])
            if n != int(n) or n < 0:
                raise MatlabError("N must be a non-negative integer.")
            if k_ > n:
                raise MatlabError("K must be an integer between 0 and N.")
            exact = math.comb(int(n), k_)
            if exact > 2**53:
                print(f"Warning: Result may not be exact. Coefficient is "
                      f"greater than {float(2**53):.6e} and is only accurate "
                      f"to 15 digits")
            return float(exact)
        flat = a.reshape(-1)
        import itertools
        combos = list(itertools.combinations(range(flat.size), k_))
        if k_ > flat.size:
            return np.zeros((0, k_), flat.dtype)
        out = np.array([[flat[i] for i in c] for c in combos],
                       flat.dtype).reshape(len(combos), k_)
        return out.reshape(-1) if out.shape[0] == 1 else out

    def f_primes(self, n):
        top = float(_mr._scalar_of(n))
        if not math.isfinite(top):
            raise MatlabError("N must be a real finite scalar.")
        top = int(math.floor(top))
        if top < 2:
            return np.zeros(0)
        sieve = np.ones(top + 1, bool)
        sieve[:2] = False
        for p in range(2, int(top ** 0.5) + 1):
            if sieve[p]:
                sieve[p * p::p] = False
        return np.flatnonzero(sieve).astype(float)

    def f_isprime(self, x):
        a = _real(x, "isprime")
        if np.any((np.fix(a) != a) | (a < 0)):
            raise MatlabError("All entries must be real non-negative "
                              "integers.")
        if np.any(a > 2**53):
            raise MatlabError("isprime needs values no larger than "
                              "flintmax (2^53).")
        out = np.array([_is_prime(int(v)) for v in a.reshape(-1)],
                       bool).reshape(a.shape)
        return bool(out.reshape(-1)[0]) if out.size == 1 \
            and np.ndim(x) == 0 else _shaped(out)

    @_nargout
    def f_gcd(self, a, b, nargout=1):
        x, y, shape = _int_pair(a, b, "gcd")
        rows = [_egcd(p, q) for p, q in zip(x, y)]
        outs = [_shaped(np.array([r[k] for r in rows], float).reshape(shape))
                for k in range(3)]
        return tuple(outs[:nargout]) if nargout > 1 else outs[0]

    def f_lcm(self, a, b):
        x, y, shape = _int_pair(a, b, "lcm")
        vals = [abs(p * q) // math.gcd(p, q) if p and q else 0
                for p, q in zip(x, y)]
        return _shaped(np.array(vals, float).reshape(shape))

    # ── special functions ───────────────────────────────────────

    def f_erf(self, x):
        return _special("erf", x)

    def f_erfc(self, x):
        return _special("erfc", x)

    def f_erfinv(self, x):
        return _special("erfinv", x)

    def f_erfcinv(self, x):
        return _special("erfcinv", x)

    def f_gamma(self, x):
        from scipy import special
        a = _real(x, "gamma")
        out = special.gamma(a)
        # MATLAB: Inf at 0 and the negative integers (scipy gives NaN).
        poles = (a <= 0) & (np.fix(a) == a)
        out = np.where(poles, np.inf, out)
        return _shaped(np.asarray(out, float))

    def f_gammaln(self, x):
        a = _real(x, "gammaln")
        if np.any(a < 0):
            raise MatlabError("Input must be nonnegative.")
        from scipy import special
        return _shaped(np.asarray(special.gammaln(a), float))

    def f_beta(self, z, w):
        return _beta_like("beta", z, w)

    def f_betaln(self, z, w):
        return _beta_like("betaln", z, w)

    def f_nthroot(self, x, n):
        a, m = _real(x, "nthroot"), _real(n, "nthroot")
        a, m = np.broadcast_arrays(a, m)
        odd = (np.fix(m) == m) & (np.mod(m, 2) == 1)
        if np.any((a < 0) & ~odd):
            raise MatlabError("If X is negative, N must be an odd integer.")
        with np.errstate(all="ignore"):
            y = np.sign(a) * np.abs(a) ** (1.0 / m)
            # MATLAB's one Newton step, so 27^(1/3) is exactly 3.
            fix = (y != 0) & np.isfinite(y) & np.isfinite(m)
            corr = np.where(fix, (y ** m - a) / (m * y ** (m - 1)), 0.0)
        y = y - corr
        return _shaped(np.asarray(y, float), x, n)


# ──────────────────────────────────────────────────────────────
#  Helpers
# ──────────────────────────────────────────────────────────────

_CASE = re.IGNORECASE if os.name == "nt" else 0

_MANY_DATES = ("datestr of several dates returns a char matrix, which Evans "
               "doesn't have; call datestr on each date.")


def _wild(pattern: str) -> str:
    """A MATLAB ``*`` wildcard as a regular expression."""
    return ".*".join(re.escape(p) for p in pattern.split("*"))


def _columns(names: list[str], width: int = 80) -> list[str]:
    w = max(len(n) for n in names) + 2
    per = max(1, width // w)
    return ["".join(n.ljust(w) for n in names[i:i + per]).rstrip()
            for i in range(0, len(names), per)]


def _value_shape(value) -> tuple[int, int]:
    if isinstance(value, list) and not isinstance(value, (Cell,
                                                          StructArray)):
        return (1, len(value))         # varargin
    return _shape(value)


def _class_of(lib, value) -> str:
    if isinstance(value, list) and not isinstance(value, (Cell,
                                                          StructArray)):
        return "cell"
    return lib.f_class(value)


def _is_complex(value) -> bool:
    if isinstance(value, complex):
        return True
    return isinstance(value, np.ndarray) and np.iscomplexobj(value)


def _bytes(value) -> int:
    """
    What ``whos`` counts. Exact for numbers, text and logicals; cells and
    structs add MATLAB's per-element header (112 bytes) only roughly.
    """
    if isinstance(value, str):
        return 2 * len(value)
    if isinstance(value, (bool, np.bool_)):
        return 1
    if isinstance(value, complex):
        return 16
    if isinstance(value, (int, float, np.number)):
        return 8
    if isinstance(value, np.ndarray):
        if value.dtype == object:
            return 8 * value.size
        return int(value.size * value.dtype.itemsize) \
            if value.dtype != bool else int(value.size)
    if isinstance(value, StructArray):
        return sum(_bytes(s) for s in value)
    if isinstance(value, list):
        return sum(112 + _bytes(v) for v in value)
    if isinstance(value, Struct):
        return sum(112 + _bytes(v) for v in value.values())
    if _is_function(value):
        return 32
    if _is_sym(value):
        return 8
    num = getattr(value, "num", None)
    if num is not None:                      # a transfer function
        return 8 * sum(np.size(c) for row in num for c in row) \
            + 8 * sum(np.size(c) for row in value.den for c in row)
    a = getattr(value, "A", None)
    if a is not None:                        # a state-space model
        return 8 * sum(np.size(getattr(value, m)) for m in "ABCD")
    return 0


def _is_builtin(lib, name: str) -> bool:
    if name in lib.names:
        return True
    # A console command, not a preset value: ``s`` is a system, and a
    # system is callable in Python without being a function.
    return _mr._is_function(lib.rt.base.get(name))


def _on_path(rt, name: str) -> str | None:
    for folder in [rt.folder, *rt.path]:
        full = os.path.join(folder, name)
        if os.path.isfile(full):
            return os.path.normpath(full)
    return None


def _folder_listing(folder: str, dots: bool = True):
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return []
    head = [".", ".."] if dots else []
    return [(n, folder, os.path.normpath(os.path.join(folder, n)))
            for n in head + names]


def _dir_struct(name: str, folder: str, full: str) -> Struct:
    try:
        st = os.stat(full)
        stamp = _dt.datetime.fromtimestamp(st.st_mtime)
        isdir = os.path.isdir(full)
        size = 0 if isdir else st.st_size
    except OSError:
        stamp, isdir, size = _dt.datetime.now(), False, 0
    dn = float(_datenum_of(stamp.year, stamp.month, stamp.day, stamp.hour,
                           stamp.minute,
                           stamp.second + stamp.microsecond / 1e6))
    return Struct(name=name, folder=os.path.normpath(folder),
                  date=_format_date(dn, "dd-mmm-yyyy HH:MM:SS"),
                  bytes=size, isdir=isdir, datenum=dn)


def _outputs(values: tuple, nargout: int):
    return values[:nargout] if nargout > 1 else values[0]


def _status(action, nargout: int, prefix: str):
    """
    Run a file operation. With outputs, failure is ``status = false`` and a
    message; without, it is an error.
    """
    try:
        action()
    except MatlabError as exc:
        if not nargout:
            raise
        return _outputs((False, str(exc), exc.identifier or prefix
                         + "OSError"), nargout)
    return _outputs((True, "", ""), nargout) if nargout else None


def _decode(raw: bytes) -> str:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("oem" if os.name == "nt" else "latin-1",
                          errors="replace")
    return text.replace("\r\n", "\n")


def _stop_requested(rt) -> bool:
    """Give the window a turn, so a Stop click lands; was it pressed?"""
    tracer = rt.tracer
    if tracer is None:
        return False
    if tracer.running and tracer.poll is not None:
        tracer.poll()
    return bool(tracer.stop_requested)


def _stoppable_wait(rt, seconds: float) -> None:
    """
    Sleep in short slices, looking at the Stop button between them. A stop
    ends the wait; the next line of user code then raises ``Interrupted``.
    """
    end = time.monotonic() + seconds
    while True:
        left = end - time.monotonic()
        if left <= 0 or _stop_requested(rt):
            return
        time.sleep(min(left, _SLICE))


# ── dates ───────────────────────────────────────────────────────

def _datenum_of(y, mo, d, h=0, mi=0, s=0):
    """MATLAB's serial date number: day 1 is 1-Jan-0000."""
    y, mo, d, h, mi, s = (np.asarray(v, float) for v in (y, mo, d, h, mi, s))
    if np.any(np.fix(mo) != mo):
        raise MatlabError("datenum needs whole months; Evans doesn't "
                          "interpret fractional months.")
    y = y + np.floor((mo - 1) / 12)
    mo = np.mod(mo - 1, 12) + 1
    leap = (np.mod(y, 4) == 0) & ((np.mod(y, 100) != 0)
                                  | (np.mod(y, 400) == 0))
    days = (365 * y + np.ceil(y / 4) - np.ceil(y / 100) + np.ceil(y / 400)
            + _CUMDAYS[mo.astype(int) - 1] + ((mo > 2) & leap) + d)
    out = days + (h * 3600 + mi * 60 + s) / 86400
    return out.item() if out.ndim == 0 else out


def _ymd(day: int) -> tuple[int, int, int, int]:
    """Year, month, day and weekday (0 = Sunday) of a whole datenum."""
    shift = 0
    while day - 366 < 1:                 # before 1-Jan-0001
        day += 146097                    # 400 years, a whole number of weeks
        shift += 400
    when = _dt.date.fromordinal(day - 366)
    return when.year - shift, when.month, when.day, (when.weekday() + 1) % 7


def _datevec(dn: float) -> list[float]:
    day = math.floor(dn)
    # A datenum near today carries about 1e-5 s of rounding error.
    secs = round((dn - day) * 86400, 4)
    if secs >= 86400:
        day, secs = day + 1, secs - 86400
    y, m, d, _ = _ymd(day)
    h, rest = divmod(secs, 3600)
    mi, s = divmod(rest, 60)
    return [y, m, d, h, mi, round(s, 4)]


def _format_date(dn: float, fmt: str) -> str:
    ms_wanted = "FFF" in fmt
    unit = 86400000 if ms_wanted else 86400
    ticks = round(dn * unit)
    day, part = divmod(ticks, unit)
    ms = part * (1 if ms_wanted else 1000)
    y, mo, d, wd = _ymd(int(day))
    h, rest = divmod(ms, 3600000)
    mi, rest = divmod(rest, 60000)
    s, f = divmod(rest, 1000)
    twelve = "AM" in fmt or "PM" in fmt
    hh = (h % 12 or 12) if twelve else h
    values = {
        "yyyy": f"{y:04d}", "YYYY": f"{y:04d}", "yy": f"{y % 100:02d}",
        "YY": f"{y % 100:02d}", "mmmm": _MONTHS[mo - 1],
        "mmm": _MONTHS[mo - 1][:3], "mm": f"{mo:02d}",
        "m": _MONTHS[mo - 1][0], "dddd": _DAYS[wd], "ddd": _DAYS[wd][:3],
        "dd": f"{d:02d}", "d": _DAYS[wd][0], "HH": f"{hh:02d}",
        "MM": f"{mi:02d}", "SS": f"{s:02d}", "FFF": f"{f:03d}",
        "AM": "AM" if h < 12 else "PM", "PM": "AM" if h < 12 else "PM",
        "QQ": f"Q{(mo - 1) // 3 + 1}",
    }
    return "".join(values.get(tok, tok) for tok in _tokens(fmt))


def _tokens(fmt: str) -> list[str]:
    out, k = [], 0
    while k < len(fmt):
        for tok in _DATE_TOKENS:
            if fmt.startswith(tok, k):
                out.append(tok)
                k += len(tok)
                break
        else:
            out.append(fmt[k])
            k += 1
    return out


_PATTERNS = {
    "yyyy": r"(?P<y>\d{4})", "YYYY": r"(?P<y>\d{4})",
    "yy": r"(?P<yy>\d{2})", "YY": r"(?P<yy>\d{2})",
    "mmmm": r"(?P<mon>[A-Za-z]+)", "mmm": r"(?P<mon>[A-Za-z]{3})",
    "mm": r"(?P<mo>\d{1,2})", "dddd": r"[A-Za-z]+", "ddd": r"[A-Za-z]{3}",
    "dd": r"(?P<d>\d{1,2})", "HH": r"(?P<H>\d{1,2})",
    "MM": r"(?P<M>\d{1,2})", "SS": r"(?P<S>\d{1,2}(?:\.\d*)?)",
    "FFF": r"(?P<F>\d{1,3})", "AM": r"(?P<p>[AaPp][Mm])",
    "PM": r"(?P<p>[AaPp][Mm])",
}


def _format_regex(fmt: str) -> re.Pattern:
    parts = []
    for tok in _tokens(fmt):
        if tok in _PATTERNS:
            parts.append(_PATTERNS[tok])
        elif tok in ("m", "d", "QQ"):
            raise MatlabError(f"datenum can't read the '{tok}' date field.")
        elif tok.isspace():
            parts.append(r"\s+")
        else:
            parts.append(re.escape(tok))
    return re.compile(r"\s*" + "".join(parts) + r"\s*")


def _parse_date(text: str, fmt, pivot) -> tuple:
    formats = [fmt] if fmt else list(_PARSE_FORMATS)
    for f in formats:
        try:
            m = _format_regex(f).fullmatch(text)
        except re.error:                                # pragma: no cover
            m = None
        if not m:
            continue
        g = {k: v for k, v in m.groupdict().items() if v is not None}
        today = _dt.date.today()
        if "y" in g:
            y = int(g["y"])
        elif "yy" in g:
            start = (today.year - 50) if pivot is None else pivot
            y = start - start % 100 + int(g["yy"])
            if y < start:
                y += 100
        else:
            y = today.year
        if "mon" in g:
            names = [n.lower() for n in _MONTHS]
            word = g["mon"].lower()
            match = [k for k, n in enumerate(names)
                     if n == word or n[:3] == word]
            if not match:
                continue
            mo = match[0] + 1
        else:
            mo = int(g.get("mo", 1))
        d = int(g.get("d", 1))
        h = int(g.get("H", 0))
        if "p" in g:
            h = h % 12 + (12 if g["p"].lower() == "pm" else 0)
        mi = int(g.get("M", 0))
        s = float(g.get("S", 0)) + float(g.get("F", 0) or 0) / 1000
        if not (1 <= mo <= 12 and 1 <= d <= 31 and h < 24 and mi < 60
                and s < 60):
            continue
        return y, mo, d, h, mi, s
    shown = f" with format '{fmt}'" if fmt else ""
    raise MatlabError(f"DATENUM failed. The date '{text}' could not be "
                      f"read{shown}.")


def _looks_like_datevec(a: np.ndarray) -> bool:
    if a.shape[1] not in (3, 6) or a.size < 3:
        return False
    mo, d = a[:, 1], a[:, 2]
    return bool(np.all((mo >= 1) & (mo <= 12) & (np.fix(mo) == mo)
                       & (d >= 1) & (d <= 31)))


# ── numbers ─────────────────────────────────────────────────────

def _real(x, name: str) -> np.ndarray:
    if _is_sym(x):
        raise MatlabError(f"{name} of a symbolic value isn't supported in "
                          f"Evans yet; use double() first.")
    if isinstance(x, (str, Cell, Struct, StructArray)):
        raise MatlabError(f"{name} needs numeric input.")
    a = np.asarray(_float_array(x))
    if np.iscomplexobj(a):
        raise MatlabError("Input must be real and full.")
    return a.astype(float)


def _shaped(out: np.ndarray, *inputs):
    """A result in MATLAB's shape: scalar, 1-D row, or 2-D."""
    if out.ndim == 0:
        return _mr._scalar(out.item()) if out.dtype != bool \
            else bool(out.item())
    if out.size == 1 and out.ndim <= 2:
        v = out.reshape(-1)[0]
        return bool(v) if out.dtype == bool else float(v)
    return _normalise(out)


def _special(name: str, x):
    from scipy import special
    a = _real(x, name)
    return _shaped(np.asarray(getattr(special, name)(a), float))


def _beta_like(name: str, z, w):
    a, b = _real(z, name), _real(w, name)
    if np.any(a < 0) or np.any(b < 0):
        raise MatlabError("Input must be real and nonnegative.")
    try:
        a, b = np.broadcast_arrays(a, b)
    except ValueError:
        raise MatlabError("Arrays have incompatible sizes for this "
                          "operation.") from None
    from scipy import special
    return _shaped(np.asarray(getattr(special, name)(a, b), float))


def _int_pair(a, b, name: str):
    x, y = _real(a, name), _real(b, name)
    for v in (x, y):
        if np.any(~np.isfinite(v)) or np.any(np.fix(v) != v):
            raise MatlabError("Inputs must be real integers.")
    try:
        x, y = np.broadcast_arrays(x, y)
    except ValueError:
        raise MatlabError("Arrays have incompatible sizes for this "
                          "operation.") from None
    return ([int(v) for v in x.reshape(-1)], [int(v) for v in y.reshape(-1)],
            x.shape)


def _egcd(a: int, b: int) -> tuple[int, int, int]:
    """MATLAB's gcd.m: ``g = a*u + b*v``, by the extended Euclid steps."""
    u, v = [1, 0, abs(a)], [0, 1, abs(b)]
    while v[2]:
        q = u[2] // v[2]
        u, v = v, [u[k] - q * v[k] for k in range(3)]
    sa = (a > 0) - (a < 0)
    sb = (b > 0) - (b < 0)
    return u[2], u[0] * sa, u[1] * sb


def _is_prime(n: int) -> bool:
    """Deterministic Miller-Rabin, exact for every n below 3.3e24."""
    if n < 2:
        return False
    small = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37)
    for p in small:
        if n % p == 0:
            return n == p
    d, r = n - 1, 0
    while d % 2 == 0:
        d, r = d // 2, r + 1
    for a in small:
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(r - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def _to_base(d, base: int, n, name: str) -> str:
    if isinstance(d, str):
        d = np.array([ord(c) for c in d], float)
    a = np.asarray(_float_array(d), float)
    if a.size == 0:
        return ""
    if a.size > 1:
        raise MatlabError(f"{name} of several numbers returns a char matrix, "
                          f"which Evans doesn't have; call it on each "
                          f"number, e.g. arrayfun(@{name}, d, "
                          f"'UniformOutput', false).")
    v = float(a.reshape(-1)[0])
    if not math.isfinite(v) or v < 0 or v != int(v):
        raise MatlabError(f"{name} needs a non-negative integer; Evans "
                          f"doesn't convert negative or fractional values.")
    if v > 2**53:
        raise MatlabError(f"{name} needs a value no larger than flintmax "
                          f"(2^53).")
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    k, out = int(v), ""
    while k:
        k, r = divmod(k, base)
        out = digits[r] + out
    out = out or "0"
    width = 0 if n is None else int(_mr._scalar_of(n))
    return out.rjust(width, "0")


def _from_base(s, base: int, message: str):
    if isinstance(s, Cell):
        return np.array([_from_base(t, base, message) for t in s],
                        float).reshape(-1, 1)
    if not isinstance(s, str):
        raise MatlabError("Input must be a character vector or a cell array "
                          "of character vectors.")
    text = s.replace(" ", "")
    if not text:
        return np.zeros((0, 0))
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"[:base]
    if any(c not in digits for c in text.lower()):
        raise MatlabError(message)
    return float(int(text, base))
