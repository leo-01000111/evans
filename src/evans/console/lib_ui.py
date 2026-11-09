"""
Dialogs, ``input`` and ``ginput``.
==================================
``uigetfile``, ``uiputfile``, ``uigetdir``, ``inputdlg``, ``questdlg``,
``listdlg``, ``msgbox`` and its siblings, ``waitbar``, ``ginput``, and
``input`` and ``keyboard`` at the console prompt.

Each function works out the question and asks the installed host
(:mod:`.dialogs`); it never opens a window itself. Installed into
:class:`.matlab_runtime._Library` by :func:`install`, like
:mod:`.lib_sparse`.
"""

from __future__ import annotations

import os

import numpy as np

from . import matlab_runtime as _mr
from .dialogs import dialog_host
from .matlab_runtime import (
    Cell,
    MatlabError,
    Struct,
    _as_text,
    _nargout,
    _normalise,
)

#: A ``waitbar`` handle is its host id plus this, so ``close(h)`` can tell it
#: from a figure number.
_WAITBAR = 1_000_000

_BUTTONS = ("Yes", "No", "Cancel")


def _texts(value, who: str) -> list[str]:
    """A string, a cell of strings or a char matrix as a list of lines."""
    if isinstance(value, str):
        return [value]
    if isinstance(value, Cell):
        out = []
        for item in value:
            out.extend(_texts(item, who))
        return out
    if value is None or (isinstance(value, np.ndarray) and value.size == 0):
        return [""]
    raise MatlabError(f"{who}: expected text or a cell array of text.")


def _filters(spec) -> list[tuple[str, str]]:
    """``uigetfile``'s filter argument as (patterns, label) pairs."""
    if spec is None or (isinstance(spec, (str, np.ndarray)) and not spec):
        return [("*.*", "All Files (*.*)")]
    if isinstance(spec, str):
        spec = Cell([spec])
    if not isinstance(spec, Cell):
        raise MatlabError("The file filter must be text or a cell array.")
    out = []
    for row in spec.grid():
        patterns = _as_text(row[0])
        label = _as_text(row[1]) if len(row) > 1 else \
            f"({patterns.replace(';', ', ')})"
        out.append((patterns, label))
    return out


def _file_args(args: tuple, who: str):
    """(filter, title, default, options) from positional and name-value."""
    positional = []
    options: dict[str, object] = {}
    i = 0
    while i < len(args):
        a = args[i]
        if isinstance(a, str) and a.lower() in ("multiselect",) \
                and i + 1 < len(args):
            options["multiselect"] = _as_text(args[i + 1]).lower() == "on"
            i += 2
            continue
        positional.append(a)
        i += 1
    if len(positional) > 4:
        raise MatlabError(f"Too many input arguments to {who}.")
    positional += [None] * (3 - len(positional))
    return positional[0], positional[1], positional[2], options


def _split(path: str) -> tuple[str, str]:
    folder, name = os.path.split(path)
    return name, (folder + os.sep) if folder else ""


def _filter_index(filters, name: str) -> int:
    """The 1-based filter a picked file name matches (``uigetfile``'s idx)."""
    import fnmatch
    for k, (patterns, _) in enumerate(filters, 1):
        if any(fnmatch.fnmatch(name.lower(), p.strip().lower())
               for p in patterns.split(";")):
            return k
    return 1


class UiLibrary:
    """The dialog commands."""

    def _start_folder(self, default) -> tuple[str, str]:
        """(folder, file name) a dialog starts in, from a name or a path."""
        text = _as_text(default) if default else ""
        if not text:
            return self.rt.resolve("."), ""
        full = self.rt.resolve(text)
        if text.endswith(("/", "\\")) or os.path.isdir(full):
            return full, ""
        return os.path.dirname(full), os.path.basename(text)

    @_nargout
    def f_uigetfile(self, *args, nargout=1):
        filt, title, default, options = _file_args(args, "uigetfile")
        multiple = bool(options.get("multiselect"))
        folder, name = self._start_folder(default)
        picked = dialog_host().open_files(
            _as_text(title) if title else "Select File to Open",
            _filters(filt), os.path.join(folder, name) if name else folder,
            multiple)
        if not picked:
            return (0.0, 0.0, 0.0)[:max(nargout, 1)] if nargout > 1 else 0.0
        picked = [os.path.normpath(p) for p in picked]
        names = [os.path.basename(p) for p in picked]
        where = os.path.dirname(picked[0])
        where += os.sep if where else ""
        first = names[0]
        shown = Cell(names) if multiple else first
        index = _filter_index(_filters(filt), first)
        return (shown, where, float(index))[:max(nargout, 1)] \
            if nargout > 1 else shown

    @_nargout
    def f_uiputfile(self, *args, nargout=1):
        filt, title, default, _ = _file_args(args, "uiputfile")
        folder, name = self._start_folder(default)
        filters = _filters(filt)
        if not name:
            name = "Untitled"
            first = filters[0][0].split(";")[0].strip()
            if first.startswith("*.") and "*" not in first[2:]:
                name += first[1:]
        path = dialog_host().save_file(
            _as_text(title) if title else "Select File to Write", filters,
            os.path.join(folder, name))
        if not path:
            return (0.0, 0.0, 0.0)[:max(nargout, 1)] if nargout > 1 else 0.0
        file, where = _split(os.path.normpath(path))
        index = _filter_index(filters, file)
        return (file, where, float(index))[:max(nargout, 1)] \
            if nargout > 1 else file

    def f_uigetdir(self, start=None, title=None):
        folder, _ = self._start_folder(start)
        picked = dialog_host().directory(
            _as_text(title) if title else "Select Folder", folder)
        return os.path.normpath(picked) if picked else 0.0

    def f_inputdlg(self, prompt="Input", title="Input", dims=None,
                   definput=None, *_):
        prompts = _texts(prompt, "inputdlg")
        lines = [1] * len(prompts)
        if dims is not None and np.size(dims):
            d = np.asarray(dims, float)
            if d.size == 1:
                lines = [int(d.reshape(-1)[0])] * len(prompts)
            elif d.size == 2:
                lines = [int(d.reshape(-1)[0])] * len(prompts)
            elif d.ndim == 2 and d.shape[0] == len(prompts):
                lines = [int(v) for v in d[:, 0]]
        defaults = [""] * len(prompts)
        if definput is not None and not (isinstance(definput, np.ndarray)
                                         and definput.size == 0):
            given = _texts(definput, "inputdlg")
            if len(given) != len(prompts):
                raise MatlabError("The default input must have as many "
                                  "entries as there are prompts.")
            defaults = given
        answer = dialog_host().form(prompts, _as_text(title), lines,
                                    defaults)
        if answer is None:
            return Cell()
        return Cell(list(answer), rows=len(answer))

    def _box(self, kind: str, message, title, nargout: int):
        text = "\n".join(_texts(message, kind))
        dialog_host().message(kind, text, _as_text(title) if title else "")
        return 1.0 if nargout else None

    @_nargout
    def f_msgbox(self, message="", title="", icon="none", *_, nargout=0):
        kind = "msg"
        if isinstance(icon, str):
            kind = {"error": "error", "warn": "warn", "help": "help"}.get(
                icon.lower(), "msg")
        elif isinstance(icon, Struct):
            kind = "msg"
        return self._box(kind, message, title, nargout)

    @_nargout
    def f_errordlg(self, message="This is the default error string.",
                   title="Error Dialog", *_, nargout=0):
        return self._box("error", message, title, nargout)

    @_nargout
    def f_warndlg(self, message="This is the default warning string.",
                  title="Warning Dialog", *_, nargout=0):
        return self._box("warn", message, title, nargout)

    @_nargout
    def f_helpdlg(self, message="This is the default help string.",
                  title="Help Dialog", *_, nargout=0):
        return self._box("help", message, title, nargout)

    def f_questdlg(self, question, title="Question Dialog", *rest):
        buttons = [_as_text(b) for b in rest]
        if not buttons:
            names, default = list(_BUTTONS), "Yes"
        elif len(buttons) == 1:
            names, default = list(_BUTTONS), buttons[0]
            if default not in _BUTTONS:
                raise MatlabError("The default button must be Yes, No or "
                                  "Cancel.")
        elif len(buttons) == 2:
            names, default = buttons, buttons[0]
        elif len(buttons) == 3:
            names, default = buttons[:2], buttons[2]
            if default not in names:
                names, default = buttons, buttons[0]
        elif len(buttons) == 4:
            names, default = buttons[:3], buttons[3]
        else:
            raise MatlabError("questdlg takes at most three buttons and a "
                              "default.")
        if default not in names:
            raise MatlabError("The default button must be one of the "
                              "buttons.")
        answer = dialog_host().question(
            "\n".join(_texts(question, "questdlg")), _as_text(title), names,
            default)
        return answer if answer in names else ""

    @_nargout
    def f_listdlg(self, *args, nargout=1):
        options = {"selectionmode": "multiple", "name": "",
                   "promptstring": "", "initialvalue": [1]}
        items = None
        if len(args) % 2:
            raise MatlabError("listdlg takes name-value pairs.")
        for k in range(0, len(args), 2):
            key = _as_text(args[k]).lower()
            if key == "liststring":
                items = _texts(args[k + 1], "listdlg")
            elif key in options:
                options[key] = args[k + 1]
            elif key not in ("listsize", "okstring", "cancelstring",
                             "uh", "fus"):
                raise MatlabError(f"Unknown listdlg option '{args[k]}'.")
        if items is None:
            raise MatlabError("listdlg needs a 'ListString'.")
        multiple = _as_text(options["selectionmode"]).lower() == "multiple"
        initial = [int(v) - 1 for v in np.atleast_1d(
            np.asarray(options["initialvalue"], float))]
        picked = dialog_host().choose(
            items, _as_text(options["name"]),
            "\n".join(_texts(options["promptstring"], "listdlg"))
            if options["promptstring"] else "", multiple, initial)
        if not picked:
            result = (np.zeros((0, 0)), 0.0)
        else:
            idx = np.array(sorted(int(i) + 1 for i in picked), float)
            result = (_normalise(idx.reshape(-1, 1) if idx.size > 1
                                 else idx), 1.0)
        return result[:max(nargout, 1)] if nargout > 1 else result[0]

    @_nargout
    def f_waitbar(self, fraction=0.0, *rest, nargout=0):
        handle = None
        text = ""
        title = ""
        args = list(rest)
        if args and not isinstance(args[0], str):
            handle = args.pop(0)
        if args:
            text = "\n".join(_texts(args.pop(0), "waitbar"))
        while len(args) >= 2:
            key = _as_text(args.pop(0)).lower()
            value = args.pop(0)
            if key == "name":
                title = _as_text(value)
        x = float(np.asarray(fraction, float).reshape(-1)[0])
        if not 0 <= x <= 1:
            raise MatlabError("The waitbar fraction must be between 0 and "
                              "1.")
        ident = None
        if handle is not None:
            ident = int(np.asarray(handle).reshape(-1)[0]) - _WAITBAR
            if ident < 1:
                raise MatlabError("Invalid waitbar handle.")
        ident = dialog_host().waitbar(ident, x, text, title)
        return float(ident + _WAITBAR) if nargout else None

    @_nargout
    def f_ginput(self, count=None, nargout=1):
        n = None if count is None else int(np.asarray(count).reshape(-1)[0])
        if n is not None and n < 0:
            raise MatlabError("The number of points must not be negative.")
        pts = dialog_host().points(n)
        if n is not None:
            pts = pts[:n]
        x = np.array([p[0] for p in pts], float)
        y = np.array([p[1] for p in pts], float)
        b = np.array([p[2] if len(p) > 2 else 1 for p in pts], float)
        col = (lambda v: _normalise(v.reshape(-1, 1)) if v.size
               else np.zeros((0, 1)))
        if nargout <= 1:
            return _normalise(np.column_stack([x, y])) if pts \
                else np.zeros((0, 2))
        return (col(x), col(y), col(b))[:nargout]

    # ── the console prompt ──────────────────────────────────────

    def _prompt_line(self, prompt) -> str:
        line = dialog_host().read_line(_as_text(prompt))
        if line is None:
            raise MatlabError("input() needs a keyboard; there is no "
                              "prompt to type at here. Set the value in "
                              "the script instead.")
        return line

    def f_input(self, prompt="", kind=None):
        line = self._prompt_line(prompt)
        if kind is not None:
            if _as_text(kind).lower() != "s":
                raise MatlabError("The second argument to input must be "
                                  "'s'.")
            return line
        if not line.strip():
            return np.zeros((0, 0))
        return self.rt.evaluate(line)

    def f_keyboard(self):
        """Read and run commands until ``return`` or ``dbcont``."""
        print("K>> type 'return' to continue the script")
        while True:
            line = self._prompt_line("K>> ")
            if line.strip() in ("return", "dbcont", "dbquit"):
                return None
            if not line.strip():
                continue
            try:
                self.f_eval(line)
            except MatlabError as exc:
                print(f"Error: {exc}")


# ── installation ──────────────────────────────────────────────────

_installed = False


def install() -> None:
    """Add the dialog functions to the library. Idempotent."""
    global _installed
    if _installed:
        return
    _installed = True
    lib = _mr._Library
    for name in dir(UiLibrary):
        if name.startswith("f_"):
            setattr(lib, name, getattr(UiLibrary, name))
    lib._start_folder = UiLibrary._start_folder
    lib._box = UiLibrary._box
    lib._prompt_line = UiLibrary._prompt_line
    _wrap_close(lib, "close")
    _wrap_close(lib, "delete")


def _wrap_close(lib, name: str) -> None:
    """``close(h)`` and ``delete(h)`` also close a ``waitbar``'s window."""
    orig = getattr(lib, f"f_{name}")

    def method(self, *args, **kwargs):
        if len(args) == 1 and isinstance(args[0], (int, float, np.number)) \
                and not isinstance(args[0], bool) \
                and args[0] >= _WAITBAR:
            dialog_host().close_waitbar(int(args[0]) - _WAITBAR)
            return None
        return orig(self, *args, **kwargs)
    method.__doc__ = orig.__doc__
    method.__name__ = orig.__name__
    for attr in ("_ml_nargout", "_ml_function", "_ml_names"):
        if hasattr(orig, attr):
            setattr(method, attr, getattr(orig, attr))
    setattr(lib, f"f_{name}", method)
