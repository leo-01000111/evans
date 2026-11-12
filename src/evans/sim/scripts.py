"""
Scripts a model runs: on open, before every run.
================================================
A model can name ``.m`` files that set up what its blocks read: ``Kp``,
``Ts``, the plant's matrices. Each is ticked to run when the model opens,
before every run, or both, and they run in their listed order in the console
workspace, so block parameters that name those variables resolve when the
model compiles (:mod:`.workspace`). This is what a Simulink model's
PreLoadFcn and InitFcn are used for; ``set_param(model, 'PreLoadFcn', …)``
and ``'InitFcn'`` edit the same list (:func:`set_callback`).

Paths are kept relative to the model file where they can be, with ``/``
separators, so a model and its scripts can move together. A script that is
not there is a warning that names it when the model opens, and stops a run
(the run would only fail later, less clearly, on the variable it defines).

Qt-free: the Model tab and the console each pass in how to run one file and
where to say things (:func:`run_scripts`), and the trust check is a plain
function of the path and the list of trusted ones (:func:`needs_trust`).
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: When a script runs: the flag on :class:`ModelScript` for each.
ON_OPEN = "on_open"
BEFORE_RUN = "before_run"
#: How each is said to people.
WHEN_TEXT = {ON_OPEN: "on open", BEFORE_RUN: "before the run"}
#: Simulink's callback parameter for each.
CALLBACKS = {"preloadfcn": ON_OPEN, "initfcn": BEFORE_RUN}


@dataclass
class ModelScript:
    """One ``.m`` file a model runs, and when."""

    #: As stored: relative to the model file (``/`` separators) or absolute.
    path: str
    on_open: bool = False
    before_run: bool = False

    @property
    def name(self) -> str:
        """The file's name, which is how messages refer to it."""
        return self.path.replace("\\", "/").rsplit("/", 1)[-1]

    def runs(self, when: str) -> bool:
        return bool(getattr(self, when))

    def to_entry(self) -> dict[str, Any]:
        return {"path": self.path, "on_open": self.on_open,
                "before_run": self.before_run}

    @classmethod
    def from_entry(cls, entry: Any) -> ModelScript | None:
        """An entry read from a file; None if it names no file at all."""
        if not isinstance(entry, dict):
            return None
        path = str(entry.get("path") or "").strip()
        if not path:
            return None
        return cls(path, bool(entry.get("on_open", False)),
                   bool(entry.get("before_run", False)))


class ScriptError(Exception):
    """A model script failed, or is not there; the run it was for stops."""

    def __init__(self, script: str, message: str,
                 line: int | None = None) -> None:
        self.script = script
        self.message = message
        self.line = line
        where = f", line {line}" if line else ""
        super().__init__(f"model script {script}{where}: {message}")


# ── paths ───────────────────────────────────────────────────────

def stored_path(file: str | Path, model_path: str | Path | None) -> str:
    """
    How ``file`` is kept in the model: relative to the model's folder when
    there is one and both are on the same drive, else absolute.
    """
    file = Path(file).resolve()
    if model_path is not None:
        try:
            rel = os.path.relpath(file, Path(model_path).resolve().parent)
        except ValueError:                  # another drive, on Windows
            rel = None
        if rel is not None:
            return rel.replace("\\", "/")
    return str(file)


def resolve(script: ModelScript | str, model_path: str | Path | None,
            search: Iterable[str | Path] = ()) -> Path | None:
    """
    The file a script entry means, or None if it is not there.

    A relative path is looked for beside the model first, then in each of
    ``search`` (the console's current folder and path), as a script called
    by name would be.
    """
    text = script.path if isinstance(script, ModelScript) else script
    path = Path(text)
    if path.is_absolute():
        return path if path.is_file() else None
    folders: list[Path] = []
    if model_path is not None:
        folders.append(Path(model_path).resolve().parent)
    folders += [Path(f) for f in search]
    for folder in folders:
        candidate = folder / path
        if candidate.is_file():
            return Path(os.path.normpath(candidate))
    return None


def rebase(scripts: list[ModelScript], old: str | Path | None,
           new: str | Path) -> None:
    """
    Keep relative script paths pointing at the same files when the model is
    saved somewhere else. A script that cannot be found is left as it was.
    """
    if old is None:
        return
    old_dir = Path(old).resolve().parent
    if old_dir == Path(new).resolve().parent:
        return
    for script in scripts:
        if Path(script.path).is_absolute():
            continue
        target = old_dir / script.path
        if target.is_file():
            script.path = stored_path(target, new)


# ── running ─────────────────────────────────────────────────────

#: Runs one file; returns ``(message, line)`` if it failed, else None.
RunOne = Callable[[Path, ModelScript], "tuple[str, int | None] | None"]


def due(scripts: Iterable[ModelScript], when: str) -> list[ModelScript]:
    """The scripts that run ``when`` (:data:`ON_OPEN` or :data:`BEFORE_RUN`),
    in order."""
    return [s for s in scripts if s.runs(when)]


def run_scripts(scripts: Iterable[ModelScript], when: str, run_one: RunOne,
                *, model_path: str | Path | None = None,
                search: Iterable[str | Path] = (),
                warn: Callable[[str], None] = lambda _text: None) -> int:
    """
    Run the scripts due ``when``, in order. Returns how many ran.

    On open, a missing script is a warning and a failing one is reported
    (by ``run_one``) without stopping the rest: the model opens either way.
    Before a run, either one raises :class:`ScriptError`, which stops it.
    """
    search = list(search)
    count = 0
    for script in due(scripts, when):
        path = resolve(script, model_path, search)
        if path is None:
            if when == BEFORE_RUN:
                raise ScriptError(script.name, (
                    f"not found ({script.path}); untick it in Model scripts "
                    f"or put the file back"))
            warn(f"Model script {script.name} was not found "
                 f"({script.path}); it did not run.")
            continue
        failure = run_one(path, script)
        count += 1
        if failure is not None and when == BEFORE_RUN:
            message, line = failure
            raise ScriptError(script.name, message, line)
    return count


# ── trust ───────────────────────────────────────────────────────

def path_key(path: str | Path) -> str:
    """The same file however it was spelled, for the trusted list."""
    return os.path.normcase(str(Path(path).resolve()))


def needs_trust(scripts: Iterable[ModelScript], when: str,
                model_path: str | Path | None,
                trusted: Iterable[str]) -> bool:
    """
    Whether to ask before running the scripts due ``when``.

    Only for a model opened from a file that is not on the ``trusted`` list
    (which holds the files the user saved from Evans and the ones they chose
    to trust), and only if it has scripts to run. A model built in this
    session has no file and is the user's own.
    """
    if model_path is None or not due(scripts, when):
        return False
    return path_key(model_path) not in {os.path.normcase(t) for t in trusted}


# ── Simulink's callback parameters ──────────────────────────────

_NAME = re.compile(r"^[^;,\s'\"()=]+$")


def callback_text(scripts: Iterable[ModelScript], when: str) -> str:
    """``get_param(model, 'InitFcn')``: the scripts as MATLAB would call
    them, ``'setup; gains'``."""
    names = []
    for script in due(scripts, when):
        path = script.path
        if "/" not in path and "\\" not in path and path.endswith(".m"):
            path = path[:-2]
        names.append(path)
    return "; ".join(names)


def parse_callback(text: str) -> list[str]:
    """
    The scripts a callback string names, as paths ending ``.m``.

    Evans runs files, not code typed into the model: ``'setup'`` or
    ``'params.m; gains.m'`` are fine, ``'Kp = 2;'`` is refused with what to
    do instead.
    """
    names: list[str] = []
    for token in re.split(r"[;,\n]", text):
        token = token.strip()
        if not token:
            continue
        if not _NAME.match(token):
            raise ValueError(
                f"Evans runs scripts from the model, not code: name .m files "
                f"(e.g. 'setup' or 'params.m; gains.m') and put "
                f"'{token}' in one of them.")
        if not token.lower().endswith(".m"):
            token += ".m"
        if token not in names:
            names.append(token)
    return names


def set_callback(scripts: list[ModelScript], when: str, text: str) -> None:
    """
    ``set_param(model, 'InitFcn', text)``: exactly the scripts ``text``
    names run ``when``, in that order. Scripts dropped from it keep their
    other flag, or leave the list if that was their only one.
    """
    names = parse_callback(text)

    def key(path: str) -> str:
        return os.path.normcase(path.replace("\\", "/"))

    wanted = [key(n) for n in names]
    existing = {key(s.path): s for s in scripts}
    first = next((i for i, s in enumerate(scripts)
                  if key(s.path) in wanted), len(scripts))
    for script in scripts:
        setattr(script, when, False)
    listed = []
    for name, k in zip(names, wanted):
        script = existing.get(k) or ModelScript(name)
        setattr(script, when, True)
        listed.append(script)
    before = [s for s in scripts[:first]
              if key(s.path) not in wanted and (s.on_open or s.before_run)]
    after = [s for s in scripts[first:]
             if key(s.path) not in wanted and (s.on_open or s.before_run)]
    scripts[:] = before + listed + after
