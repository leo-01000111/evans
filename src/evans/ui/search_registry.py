"""
What the command palette can do: :func:`collect` lists it, fresh each time.

Built when the palette opens, so it is never stale (a new recent file, a new
script tab, an action enabled since) and costs nothing at startup. The
entries are:

* every enabled action reachable from the menu bar, walked recursively (the
  *Open recent* and *Examples* submenus are skipped there: their files and
  models have entries of their own below);
* Analyse: a pane kind each, the three layouts, the presets, the Design
  pages, Take snapshot;
* Model: a block each, the toolbar's Run · Stop · Linearise · Scripts,
  every example;
* Console: a help page each, the open scripts;
* global: the recent files.

An entry that belongs to another workspace switches to it first.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from PySide6.QtGui import QAction, QKeySequence

from .. import help as pages
from . import help as help_window
from . import keys
from .panes import PANE_KINDS
from .search import Entry
from .workspace import Workspace

#: A menu with this dynamic property set is not walked (its items have
#: entries of their own).
SKIP_PROPERTY = "searchSkip"
#: An action's workspace is its `workspace` property (a Workspace's value).
WORKSPACE_PROPERTY = "workspace"

_LAYOUT_TITLES = {1: "One pane", 2: "Two panes", 4: "Four panes"}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _clean(text: str) -> str:
    """A menu title as shown: no mnemonic ampersand, no tab-and-shortcut."""
    return text.split("\t")[0].replace("&&", "\0").replace("&", "") \
        .replace("\0", "&").strip()


def portable_shortcut(action: QAction) -> str:
    """All of the action's shortcuts, as "Ctrl+K / Ctrl+Shift+P"."""
    return " / ".join(k.toString(QKeySequence.PortableText)
                      for k in action.shortcuts())


def workspace_of(action: QAction) -> Workspace | None:
    value = action.property(WORKSPACE_PROPERTY)
    try:
        return Workspace(value) if value else None
    except ValueError:
        return None


def menu_actions(window, *, disabled: bool = False):
    """
    ``(path, action)`` for every enabled, non-separator action in the menu
    bar (``disabled``: those too), where ``path`` is the titles from the top
    menu down. The same walk the palette uses, so a test can check that
    nothing is missed.
    """
    def walk(menu, path):
        for action in menu.actions():
            if action.isSeparator():
                continue
            sub = action.menu()
            if sub is not None:
                if not sub.property(SKIP_PROPERTY):
                    yield from walk(sub, [*path, _clean(sub.title())])
                continue
            if (disabled or action.isEnabled()) and _clean(action.text()):
                yield [*path, _clean(action.text())], action

    for top in window.menuBar().actions():
        menu = top.menu()
        if menu is not None:
            yield from walk(menu, [_clean(menu.title())])


#: Titles that do not follow the stack ("Undo Add block") on the sheet.
_STABLE_TITLES = {"edit.undo": "Undo", "edit.redo": "Redo"}


def collect(window, *, for_sheet: bool = False) -> list[Entry]:
    """
    Every entry the palette offers right now, in no particular order.

    ``for_sheet`` is the shortcut sheet's view of it: disabled actions stay
    (Undo is no less a shortcut for being greyed out) and keep fixed titles.
    """
    entries: list[Entry] = []
    used: set[str] = set()

    def add(entry_id: str, title: str, section: str,
            workspace: Workspace | None, run: Callable[[], None], *,
            shortcut: str = "", keywords: tuple[str, ...] = (),
            switch: bool = True, source=None) -> None:
        base, n = entry_id, 2
        while entry_id in used:
            entry_id = f"{base}.{n}"
            n += 1
        used.add(entry_id)

        def go() -> None:
            if switch and workspace is not None:
                window.show_workspace(workspace)
            run()

        entries.append(Entry(entry_id, title, section, workspace,
                             keys.label(shortcut), keywords, go, source))

    # ── the menus ──
    for path, action in menu_actions(window, disabled=for_sheet):
        entry_id = action.objectName() or ".".join(_slug(p) for p in path)
        if for_sheet:
            path = [*path[:-1], _STABLE_TITLES.get(entry_id, path[-1])]
        add(entry_id, path[-1], path[0], workspace_of(action), action.trigger,
            shortcut=portable_shortcut(action),
            keywords=tuple(p for p in path[1:-1]), source=action)

    # ── Analyse ──
    for kind in PANE_KINDS:
        add(f"pane.{kind.key}", f"Show {kind.label}", "Analyse",
            Workspace.ANALYSE,
            lambda k=kind.key: window.show_pane_kind(k),
            keywords=(kind.key, "plot", "pane"))
    for count in (1, 2, 4):
        add(f"layout.{count}", f"Layout: {_LAYOUT_TITLES[count].lower()}",
            "Analyse", Workspace.ANALYSE,
            lambda n=count: window.set_pane_layout(n), keywords=("panes", "grid"))
    for label, method in window._PRESETS:
        add("preset." + method.removeprefix("_preset_"),
            f"Plant preset: {label}", "Analyse", Workspace.ANALYSE,
            lambda m=method: getattr(window, m)(), keywords=("plant", "G"))
    for mode, label in (("gain", "Gain"), ("compensator", "Compensator"),
                        ("pid", "PID")):
        add(f"design.{mode}", f"Design: {label}", "Analyse",
            Workspace.ANALYSE, lambda m=mode: window.show_design(m),
            keywords=("tune", "controller"))
    add("snapshot.take", "Take snapshot", "Analyse", Workspace.ANALYSE,
        lambda: window._snapshot_bar.take(), keywords=("compare", "save design"))

    # ── Model ──
    sim = window._sim_tab
    from ..sim.block import by_category
    for category, blocks in by_category().items():
        for cls in blocks:
            add(f"block.{cls.type_name}", f"Add block: {cls.type_name}",
                "Blocks", Workspace.MODEL,
                lambda t=cls.type_name: sim._canvas.add_block(t),
                keywords=(category,))
    add("model.run", "Run simulation", "Model", Workspace.MODEL,
        sim.run_simulation, shortcut="Ctrl+R", keywords=("simulate", "start"))
    if sim._stop_btn.isEnabled():
        add("model.stop", "Stop simulation", "Model", Workspace.MODEL,
            sim._cancel, keywords=("cancel",))
    add("model.linearise", "Linearise model", "Model", Workspace.MODEL,
        sim.linearise, keywords=("linearize", "analyse"))
    add("model.scripts", "Model scripts…", "Model", Workspace.MODEL,
        sim.edit_model_scripts, keywords=("callbacks", "variables"))
    from ..examples import examples
    for example in examples():
        add(f"example.{_slug(example.title)}", f"Example: {example.title}",
            "Examples", Workspace.MODEL,
            lambda e=example: window.open_example(e),
            keywords=(example.summary[:40],) if example.summary else ())

    # ── Console ──
    for topic in pages.topics():
        add(f"help.{topic}", f"Help: {topic}", "Help", Workspace.CONSOLE,
            lambda t=topic: help_window.open_help(t),
            switch=False)             # a page opens its own window
    editor = window._console.editor
    for document in editor.documents():
        add(f"script.{document.key or document.name}",
            f"Script: {document.name}", "Console", Workspace.CONSOLE,
            lambda d=document: (editor.show_document(d),
                                window._console.show_script()))

    # ── global ──
    for path in window.recent_files.paths():
        add(f"recent.{path}", f"Open: {path.name}", "Recent", None,
            lambda p=path: window.open_recent(p), keywords=(str(path.parent),))
    return entries
