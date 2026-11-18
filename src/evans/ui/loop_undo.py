"""
Undo for the course loop.

The Model workspace has always had an undo stack of its own; the loop on
Analyse (the four blocks G, K1, K2, H) had none, so a plant edit, *Apply
controller*, a preset or a snapshot restore could not be taken back. One
command covers them all: it holds the loop as ``session_dict`` before and
after the change and swaps one for the other in place, so the architecture
object (which every pane, the diagram and the console hold) never changes.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtGui import QUndoCommand

from ..core.architecture import CourseArchitecture
from ..core.session import load_session_dict

#: Qt merges two commands only if both report the same non-negative id; the
#: ``merge_key`` then decides whether they really belong together.
MERGE_ID = 0x4C4F4F50


class ReplaceLoop(QUndoCommand):
    """One change to the loop, as the session dict before and after it."""

    def __init__(self, arch: CourseArchitecture, before: dict[str, Any],
                 after: dict[str, Any], text: str,
                 refresh: Callable[[], None] | None = None,
                 merge_key: str | None = None) -> None:
        super().__init__(text)
        self.arch = arch
        self.before = before
        self.after = after
        self.merge_key = merge_key
        self._refresh = refresh
        #: ``QUndoStack.push`` calls redo(); the change is already made.
        self._first = True

    def undo(self) -> None:
        load_session_dict(self.arch, self.before)
        self._notify()

    def redo(self) -> None:
        if self._first:
            self._first = False
            return
        load_session_dict(self.arch, self.after)
        self._notify()

    def _notify(self) -> None:
        if self._refresh is not None:
            self._refresh()

    def id(self) -> int:
        return MERGE_ID if self.merge_key is not None else -1

    def mergeWith(self, other: QUndoCommand) -> bool:  # noqa: N802 (Qt API)
        if not isinstance(other, ReplaceLoop) or self.merge_key is None \
                or other.merge_key != self.merge_key \
                or other.arch is not self.arch:
            return False
        self.after = other.after
        return True
