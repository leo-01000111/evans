"""
Autosave for crash recovery.

Every running Evans keeps a folder of its own under the user's app data
(``recovery/session-<pid>-<start>``). Every minute or so it writes a copy of
each document with unsaved changes there: editor scripts, the live script
and the Model tab's diagram. A copy is never written over the real file, and
each write goes to a temporary name first and is then renamed into place, so
a crash in the middle of a write leaves the previous copy whole.

A normal quit deletes the folder. A folder that is still there at the next
start, whose Evans is no longer running, is what a crash left behind, and
the window offers to restore it.

The store (:class:`RecoveryStore`) does not touch Qt, so it can be tested
by killing a real process. :class:`RecoveryController` is the timer and the
window's side of it.

Not covered: the workspace's variables (a ``save`` of them can be large and
some values cannot be written), and the command history, which
:mod:`.persist` already writes after every command.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from pathlib import Path

#: The kinds of document a copy can be of.
SCRIPT, LIVE, MODEL = "script", "live", "model"

#: How many earlier copies of the model are kept beside the newest.
MODEL_VERSIONS = 3

#: A folder whose heartbeat is older than this is abandoned even when a
#: process with its pid exists: pids are reused, and a hung Evans is as good
#: as gone. Added to three intervals, so a long interval is not misread.
STALE_AFTER = 5 * 60

LOCK = "lock.json"
MANIFEST = "manifest.json"
PREFIX = "session-"


@dataclass
class Item:
    """One unsaved document, as written to (or read from) a folder."""

    kind: str
    #: Unique within a session: ``script-3``, ``live``, ``model``.
    key: str
    #: What the user called it: the file name, or *Untitled 3*.
    title: str
    text: str
    #: The file it came from, if it was ever saved.
    path: str | None = None
    #: Anything else the kind needs back (a script's language).
    extra: dict = field(default_factory=dict)


@dataclass
class Orphan:
    """A folder left by an Evans that did not close normally."""

    folder: Path
    started: float
    items: list[Item]
    #: Earlier copies of the model, newest first.
    model_versions: list[Path] = field(default_factory=list)


# ── the store ───────────────────────────────────────────────────


class RecoveryStore:
    """One session's folder: written while Evans runs, deleted on a clean quit."""

    def __init__(self, root: str | Path, pid: int | None = None,
                 started: float | None = None) -> None:
        self.root = Path(root)
        self.pid = os.getpid() if pid is None else pid
        self.started = time.time() if started is None else started
        self.folder = self.root / f"{PREFIX}{self.pid}-{int(self.started)}"
        #: What each key's file holds now, so an unchanged one is not rewritten.
        self._written: dict[str, str] = {}

    def begin(self) -> None:
        self.folder.mkdir(parents=True, exist_ok=True)
        self.heartbeat()

    def heartbeat(self) -> None:
        _atomic_write(self.folder / LOCK, json.dumps({
            "pid": self.pid, "started": self.started,
            "heartbeat": time.time()}))

    def write(self, items: Iterable[Item]) -> int:
        """
        Make the folder hold exactly ``items``. Returns how many files were
        written (unchanged copies are left alone).
        """
        items = list(items)
        self.folder.mkdir(parents=True, exist_ok=True)
        changed = 0
        for item in items:
            if self._written.get(item.key) == item.text:
                continue
            target = self.folder / _file_name(item)
            if item.kind == MODEL and target.exists():
                _rotate(target)
            _atomic_write(target, item.text)
            self._written[item.key] = item.text
            changed += 1
        keys = {item.key for item in items}
        for key in list(self._written):
            if key not in keys:
                del self._written[key]
        # The manifest last: a copy it lists is always complete on disk.
        _atomic_write(self.folder / MANIFEST, json.dumps([
            {"kind": i.kind, "key": i.key, "title": i.title, "path": i.path,
             "extra": i.extra, "file": _file_name(i)} for i in items],
            indent=1))
        live = {_file_name(i) for i in items}
        for old in self.folder.iterdir():
            if (old.name not in live and old.name not in (LOCK, MANIFEST)
                    and not _is_model_version(old.name)):
                _unlink(old)
        self.heartbeat()
        return changed

    def finish(self) -> None:
        """A clean quit: nothing left to recover."""
        shutil.rmtree(self.folder, ignore_errors=True)
        self._written.clear()


def orphans(root: str | Path, own: Path | None = None,
            now: float | None = None,
            alive: Callable[[int], bool] | None = None) -> list[Orphan]:
    """
    The folders under ``root`` left by an Evans that is not running, oldest
    first. Empty ones are deleted on the way; one still being written by a
    running Evans is left alone.
    """
    root = Path(root)
    if not root.is_dir():
        return []
    now = time.time() if now is None else now
    alive = alive or process_alive
    found = []
    for folder in sorted(root.glob(PREFIX + "*")):
        if not folder.is_dir() or (own is not None and folder == own):
            continue
        lock = _read_json(folder / LOCK)
        if isinstance(lock, dict):
            pid = int(lock.get("pid", 0) or 0)
            beat = float(lock.get("heartbeat", 0) or 0)
            started = float(lock.get("started", 0) or 0)
        else:                       # killed before its first heartbeat
            pid, started = 0, folder.stat().st_mtime
            beat = started
        if pid and alive(pid) and now - beat < STALE_AFTER:
            continue
        items = _read_items(folder)
        if not items:
            shutil.rmtree(folder, ignore_errors=True)
            continue
        versions = sorted(
            (p for p in folder.iterdir() if _is_model_version(p.name)),
            key=lambda p: p.name)
        found.append(Orphan(folder, started, items, versions))
    found.sort(key=lambda o: o.started)
    return found


def discard(orphan: Orphan) -> None:
    shutil.rmtree(orphan.folder, ignore_errors=True)


def default_root() -> Path:
    """``recovery`` in the app's data folder; ``EVANS_RECOVERY_DIR`` wins."""
    override = os.environ.get("EVANS_RECOVERY_DIR")
    if override:
        return Path(override)
    from PySide6.QtCore import QStandardPaths
    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    return Path(base or Path.home() / ".evans") / "recovery"


def process_alive(pid: int) -> bool:
    """Whether a process with this pid is running now."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL,
                                         wintypes.DWORD]
        kernel32.GetExitCodeProcess.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel32.OpenProcess(0x1000, False, pid)  # query limited
        if not handle:
            return ctypes.get_last_error() == 5             # access denied
        code = wintypes.DWORD()
        ok = kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
        kernel32.CloseHandle(handle)
        return bool(ok) and code.value == 259               # STILL_ACTIVE
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


# ── helpers ─────────────────────────────────────────────────────


_SUFFIX = {SCRIPT: ".txt", LIVE: ".m", MODEL: ".json"}


def _file_name(item: Item) -> str:
    return item.key + _SUFFIX.get(item.kind, ".txt")


def _is_model_version(name: str) -> bool:
    """``model.1.json`` … ``model.N.json``: earlier copies of the diagram."""
    parts = name.split(".")
    return len(parts) == 3 and parts[0] == MODEL and parts[1].isdigit() \
        and parts[2] == "json"


def _rotate(current: Path) -> None:
    """model.json → model.1.json → model.2.json …, the oldest dropped."""
    folder = current.parent
    for n in range(MODEL_VERSIONS, 0, -1):
        older = folder / f"{MODEL}.{n}.json"
        newer = current if n == 1 else folder / f"{MODEL}.{n - 1}.json"
        if newer.exists():
            os.replace(newer, older)


def _atomic_write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _unlink(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


def _read_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _read_items(folder: Path) -> list[Item]:
    entries = _read_json(folder / MANIFEST)
    if not isinstance(entries, list):
        return []
    items = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        try:
            text = (folder / str(entry["file"])).read_text(encoding="utf-8")
        except (KeyError, OSError):
            continue
        items.append(Item(
            kind=str(entry.get("kind", SCRIPT)), key=str(entry.get("key", "")),
            title=str(entry.get("title", "")), text=text,
            path=entry.get("path") or None,
            extra=entry.get("extra") if isinstance(entry.get("extra"), dict)
            else {}))
    return items


# ── the window's side ───────────────────────────────────────────

#: File ▸ Autosave: whether it runs, and how often (seconds).
ENABLED_KEY = "recovery/enabled"
INTERVAL_KEY = "recovery/interval"
DEFAULT_INTERVAL = 60
INTERVALS = (30, 60, 120, 300)


def saved_enabled() -> bool:
    from . import persist
    return persist._bool(persist.settings().value(ENABLED_KEY), True)


def saved_interval() -> int:
    from . import persist
    try:
        value = int(persist.settings().value(INTERVAL_KEY) or DEFAULT_INTERVAL)
    except (TypeError, ValueError):
        return DEFAULT_INTERVAL
    return value if value in INTERVALS else DEFAULT_INTERVAL


def remember(enabled: bool, interval: int) -> None:
    from . import persist
    settings = persist.settings()
    settings.setValue(ENABLED_KEY, bool(enabled))
    settings.setValue(INTERVAL_KEY, int(interval))


class RecoveryController:
    """
    The timer. ``collect`` returns the unsaved documents as :class:`Item`s;
    each tick writes the ones that changed.
    """

    def __init__(self, collect: Callable[[], list[Item]],
                 root: str | Path | None = None,
                 interval: int = DEFAULT_INTERVAL) -> None:
        from PySide6.QtCore import QTimer

        self._collect = collect
        self.root = Path(root) if root is not None else default_root()
        self.store = RecoveryStore(self.root)
        self.interval = interval
        self._timer = QTimer()
        self._timer.timeout.connect(self.snapshot)
        self.running = False

    def start(self) -> None:
        self.store.begin()
        self._timer.start(self.interval * 1000)
        self.running = True

    def set_interval(self, seconds: int) -> None:
        self.interval = seconds
        if self.running:
            self._timer.start(seconds * 1000)

    def snapshot(self) -> int:
        """Write what changed now. Returns how many copies were written."""
        if not self.running:
            return 0
        try:
            return self.store.write(self._collect())
        except OSError:
            # A full disk or a vanished folder must not break editing; the
            # next tick tries again.
            return 0

    def stop(self) -> None:
        """A clean quit, or autosave turned off: the copies go."""
        self._timer.stop()
        self.running = False
        self.store.finish()

    def orphans(self) -> list[Orphan]:
        return orphans(self.root, own=self.store.folder)
