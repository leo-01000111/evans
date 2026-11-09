"""
Where a dialog command's question goes.

``uigetfile``, ``inputdlg``, ``msgbox``, ``waitbar``, ``ginput`` and ``input``
have to ask a person something. The same split as :mod:`.figures` and
:mod:`.apps`: the command works out what to ask and hands it to the installed
**host**, so the console stays free of Qt and a headless script, a test or a
build server never blocks on a window nobody can see.

The UI installs a host that opens real dialogs (``evans.ui.console.
dialog_host``). The default host is :class:`ScriptedDialogs`: it records each
question and answers from a queue, and with nothing queued it answers as a
person pressing *Cancel* would. That is also how the tests drive the commands.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any


class Dialogs:
    """
    What a host can do. Every method returns ``None`` for *Cancel* (or, for
    :meth:`message` and :meth:`waitbar`, nothing at all).
    """

    def open_files(self, title: str, filters: list[tuple[str, str]],
                   start: str, multiple: bool) -> list[str] | None:
        """Paths picked in an Open dialog. ``filters`` is (patterns, label)."""
        return None

    def save_file(self, title: str, filters: list[tuple[str, str]],
                  default: str) -> str | None:
        return None

    def directory(self, title: str, start: str) -> str | None:
        return None

    def form(self, prompts: list[str], title: str, lines: list[int],
             defaults: list[str]) -> list[str] | None:
        """Text fields, one per prompt; the answers, or ``None`` on Cancel."""
        return None

    def message(self, kind: str, text: str, title: str) -> None:
        """``kind`` is ``msg``, ``help``, ``warn`` or ``error``."""

    def question(self, text: str, title: str, buttons: list[str],
                 default: str) -> str | None:
        return None

    def choose(self, items: list[str], title: str, prompt: str,
               multiple: bool, initial: list[int]) -> list[int] | None:
        """0-based positions picked from a list."""
        return None

    def waitbar(self, ident: int | None, fraction: float, text: str,
                title: str) -> int:
        """Open (``ident`` is ``None``) or update a progress bar; its id."""
        return ident or 1

    def close_waitbar(self, ident: int) -> bool:
        return False

    def points(self, count: int | None) -> list[tuple[float, float, int]]:
        """Clicks on the current figure: (x, y, button); fewer on Enter."""
        return []

    def read_line(self, prompt: str) -> str | None:
        """A line typed at the console; ``None`` if nobody can type one."""
        return None


class ScriptedDialogs(Dialogs):
    """
    The default host: remembers every question, answers from ``answers``.

    ``answers[method]`` is a queue; each call takes the front one. A queued
    :class:`Exception` is raised instead, to test a failing host. With the
    queue empty the call answers as *Cancel*.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple]] = []
        self.answers: dict[str, deque] = defaultdict(deque)
        self.waitbars: dict[int, dict[str, Any]] = {}
        self._next = 0

    def queue(self, method: str, *answers: Any) -> ScriptedDialogs:
        self.answers[method].extend(answers)
        return self

    def _ask(self, method: str, *args):
        self.calls.append((method, args))
        queue = self.answers[method]
        if not queue:
            return None
        answer = queue.popleft()
        if isinstance(answer, Exception):
            raise answer
        return answer

    @property
    def last(self) -> tuple[str, tuple] | None:
        return self.calls[-1] if self.calls else None

    def asked(self, method: str) -> list[tuple]:
        return [args for name, args in self.calls if name == method]

    def open_files(self, title, filters, start, multiple):
        return self._ask("open_files", title, filters, start, multiple)

    def save_file(self, title, filters, default):
        return self._ask("save_file", title, filters, default)

    def directory(self, title, start):
        return self._ask("directory", title, start)

    def form(self, prompts, title, lines, defaults):
        return self._ask("form", prompts, title, lines, defaults)

    def message(self, kind, text, title):
        self._ask("message", kind, text, title)

    def question(self, text, title, buttons, default):
        return self._ask("question", text, title, buttons, default)

    def choose(self, items, title, prompt, multiple, initial):
        return self._ask("choose", items, title, prompt, multiple, initial)

    def waitbar(self, ident, fraction, text, title):
        if ident is None or ident not in self.waitbars:
            self._next += 1
            ident = self._next
        self.waitbars[ident] = {"fraction": fraction, "text": text,
                                "title": title}
        self.calls.append(("waitbar", (ident, fraction, text, title)))
        return ident

    def close_waitbar(self, ident):
        self.calls.append(("close_waitbar", (ident,)))
        return self.waitbars.pop(ident, None) is not None

    def points(self, count):
        return self._ask("points", count) or []

    def read_line(self, prompt):
        return self._ask("read_line", prompt)


_host: Dialogs = ScriptedDialogs()


def set_dialog_host(host: Dialogs) -> Dialogs:
    """Install the host. Returns the previous one, so it can be restored."""
    global _host
    previous, _host = _host, host
    return previous


def dialog_host() -> Dialogs:
    """The host currently installed."""
    return _host


def scripted_host() -> ScriptedDialogs:
    """A fresh scripted host, for tests and headless scripts."""
    return ScriptedDialogs()
