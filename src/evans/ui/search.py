"""
The command palette's matching and ordering. No Qt in here.

An :class:`Entry` is one thing the palette can do: an action, a block to add,
a help page. :func:`score` says how well a typed query fits a piece of text,
and :func:`rank` turns a list of entries and a query into the list the popup
shows.

The ordering is the one decision 7 of Phase 8 asks for: the palette is
context-sensitive by *ranking*, not by filtering. The current workspace's
entries come first, then the global ones, then the other workspaces' (which
switch workspace when picked). Inside a group the better match wins, then the
more recently used, then the title.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:                                  # pragma: no cover
    from .workspace import Workspace

#: The most rows `rank` returns.
LIMIT = 50
#: How many entry ids are remembered between sessions.
RECENT_LIMIT = 20


@dataclass
class Entry:
    """One line of the palette."""

    #: Stable across sessions: ``"file.save"``, ``"block.Gain"``, ``"preset.so_under"``.
    id: str
    title: str
    #: Shown muted after the title: "Analyse", "File", "Blocks", "Recent"…
    section: str
    #: None: global. Otherwise the workspace the entry belongs to.
    workspace: Workspace | None = None
    #: Already through ``keys.label``; "" for none.
    shortcut: str = ""
    keywords: tuple[str, ...] = ()
    run: Callable[[], None] = lambda: None
    #: The action behind the entry, when there is one (the shortcut sheet
    #: and the tests look at it); the palette itself never does.
    source: Any = None


def _word_start(text: str, i: int) -> bool:
    if i == 0:
        return True
    before, here = text[i - 1], text[i]
    if not before.isalnum():
        return True
    return before.islower() and here.isupper()      # camelCase: "stepResponse"


def score(query: str, text: str) -> float | None:
    """
    How well ``query`` fits ``text``, or None when it does not.

    A case-insensitive subsequence match: the letters of the query must
    appear in the text in order, not next to each other. Higher for a match
    at the start of the text, at word starts, on consecutive letters, and in
    a shorter text. An empty query matches everything with score 0.
    """
    query = "".join(query.split()).lower()
    if not query:
        return 0.0
    low = text.lower()
    # Cheap rejection first: most entries do not match, and the exact
    # alignment below is only worth computing for those that do.
    position = 0
    for letter in query:
        position = low.find(letter, position) + 1
        if position == 0:
            return None

    # best[j]: the best score with the previous query letter matched at j.
    best: dict[int, float] = {}
    for n, letter in enumerate(query):
        here: dict[int, float] = {}
        for j, char in enumerate(low):
            if char != letter:
                continue
            gain = 1.0
            if j == 0:
                gain += 4.0
            elif _word_start(text, j):
                gain += 2.0
            if n == 0:
                here[j] = gain - 0.01 * j
                continue
            options = []
            for k, value in best.items():
                if k < j:
                    options.append(value + (2.0 if k == j - 1 else -0.05 * (j - k)))
            if options:
                here[j] = gain + max(options)
        best = here
        if not best:
            return None
    return max(best.values()) - 0.02 * len(text)


def _best(entry: Entry, query: str) -> float | None:
    scores = [s for s in (score(query, entry.title),
                          *(score(query, k) for k in entry.keywords))
              if s is not None]
    return max(scores) if scores else None


def rank(entries: Iterable[Entry], query: str, current: Workspace | None,
         recent_ids: Sequence[str] = ()) -> list[Entry]:
    """
    The entries that match ``query``, best first, at most :data:`LIMIT`.

    Group order: the ``current`` workspace's entries, then the global ones,
    then the other workspaces'. Inside a group: score, then recency
    (``recent_ids``, newest first), then title. With an empty query the
    recently used entries come first, then the rest in that order.
    """
    recency = {entry_id: n for n, entry_id in enumerate(recent_ids)}
    never = len(recency)

    def group(entry: Entry) -> int:
        if entry.workspace is None:
            return 1
        return 0 if entry.workspace == current else 2

    ranked: list[tuple[tuple, Entry]] = []
    for entry in entries:
        value = _best(entry, query)
        if value is None:
            continue
        used = recency.get(entry.id, never)
        if query.strip():
            key = (group(entry), -value, used, entry.title.lower())
        else:
            key = (0 if entry.id in recency else 1,
                   used if entry.id in recency else group(entry),
                   group(entry), entry.title.lower())
        ranked.append((key, entry))
    ranked.sort(key=lambda pair: pair[0])
    return [entry for _key, entry in ranked[:LIMIT]]


def remember(recent_ids: Sequence[str], entry_id: str) -> list[str]:
    """``entry_id`` moved to the front, the list cut to :data:`RECENT_LIMIT`."""
    kept = [i for i in recent_ids if i != entry_id]
    return [entry_id, *kept][:RECENT_LIMIT]
