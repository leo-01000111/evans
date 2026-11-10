"""
Autosave for crash recovery (`evans.ui.recovery`).

The store is tested on its own, including a real process killed with work in
its folder, and then the window: what it collects, the File ▸ Autosave menu,
the offer at startup and a clean quit.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from evans.ui import recovery
from evans.ui.recovery import LIVE, MODEL, SCRIPT, Item, RecoveryStore

SRC = Path(__file__).resolve().parents[2] / "src"


def _never_alive(_pid):
    return False


def _always_alive(_pid):
    return True


# ── the store ───────────────────────────────────────────────────


def test_write_keeps_exactly_the_unsaved_items(tmp_path):
    store = RecoveryStore(tmp_path, pid=111, started=1.0)
    store.begin()
    a = Item(SCRIPT, "script-1", "Untitled 1", "x = 1")
    b = Item(SCRIPT, "script-2", "f.m", "y = 2", path="C:/f.m")
    assert store.write([a, b]) == 2
    assert store.write([a, b]) == 0               # unchanged: not rewritten
    assert store.write([a]) == 0                  # b was saved
    assert not (store.folder / "script-2.txt").exists()
    [left] = recovery.orphans(tmp_path, alive=_never_alive)
    assert [(i.key, i.text) for i in left.items] == [("script-1", "x = 1")]


def test_model_keeps_earlier_versions(tmp_path):
    store = RecoveryStore(tmp_path, pid=111, started=1.0)
    store.begin()
    for n in range(5):
        store.write([Item(MODEL, "model", "m", f'{{"v": {n}}}')])
    folder = store.folder
    assert json.loads((folder / "model.json").read_text()) == {"v": 4}
    assert json.loads((folder / "model.1.json").read_text()) == {"v": 3}
    assert json.loads((folder / "model.3.json").read_text()) == {"v": 1}
    assert not (folder / "model.4.json").exists()
    [left] = recovery.orphans(tmp_path, alive=_never_alive)
    assert [p.name for p in left.model_versions] == [
        "model.1.json", "model.2.json", "model.3.json"]


def test_finish_leaves_nothing(tmp_path):
    store = RecoveryStore(tmp_path, pid=111, started=1.0)
    store.begin()
    store.write([Item(SCRIPT, "script-1", "Untitled 1", "x")])
    store.finish()
    assert not store.folder.exists()
    assert recovery.orphans(tmp_path, alive=_never_alive) == []


def test_running_evans_is_left_alone_until_its_heartbeat_stops(tmp_path):
    store = RecoveryStore(tmp_path, pid=111, started=1.0)
    store.begin()
    store.write([Item(SCRIPT, "script-1", "Untitled 1", "x")])
    assert recovery.orphans(tmp_path, alive=_always_alive) == []
    later = time.time() + recovery.STALE_AFTER + 1
    assert len(recovery.orphans(tmp_path, now=later,
                                alive=_always_alive)) == 1


def test_own_and_empty_folders(tmp_path):
    own = RecoveryStore(tmp_path, pid=1, started=1.0)
    own.begin()
    own.write([Item(SCRIPT, "script-1", "Untitled 1", "x")])
    empty = RecoveryStore(tmp_path, pid=2, started=2.0)
    empty.begin()
    empty.write([])
    assert recovery.orphans(tmp_path, own=own.folder,
                            alive=_never_alive) == []
    assert not empty.folder.exists()              # tidied on the way


def test_a_write_cut_short_keeps_the_previous_copy(tmp_path):
    store = RecoveryStore(tmp_path, pid=111, started=1.0)
    store.begin()
    store.write([Item(SCRIPT, "script-1", "Untitled 1", "good")])
    # A crash between writing the temporary file and renaming it.
    (store.folder / "script-1.txt.tmp").write_text("hal")
    [left] = recovery.orphans(tmp_path, alive=_never_alive)
    assert left.items[0].text == "good"


def test_a_killed_process_leaves_its_work(tmp_path):
    """A real Evans-side process, killed without any cleanup."""
    script = textwrap.dedent(f"""
        import os, sys
        sys.path.insert(0, {str(SRC)!r})
        from evans.ui.recovery import RecoveryStore, Item, SCRIPT, MODEL
        store = RecoveryStore({str(tmp_path)!r})
        store.begin()
        store.write([Item(SCRIPT, "script-1", "Untitled 1", "a = 1;"),
                     Item(MODEL, "model", "loop", '{{"name": "loop"}}')])
        store.write([Item(SCRIPT, "script-1", "Untitled 1", "a = 2;"),
                     Item(MODEL, "model", "loop", '{{"name": "loop"}}')])
        os._exit(9)
    """)
    done = subprocess.run([sys.executable, "-c", script], timeout=60)
    assert done.returncode == 9
    [left] = recovery.orphans(tmp_path)           # the real liveness check
    texts = {i.key: i.text for i in left.items}
    assert texts == {"script-1": "a = 2;", "model": '{"name": "loop"}'}


def test_process_alive():
    assert recovery.process_alive(os.getpid())
    gone = subprocess.Popen([sys.executable, "-c", "pass"])
    gone.wait(timeout=60)
    assert not recovery.process_alive(gone.pid)
    assert not recovery.process_alive(0)


# ── the window ──────────────────────────────────────────────────

pytest.importorskip("PySide6", reason="Qt not available")


@pytest.fixture(scope="module")
def app():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def win(app):
    from evans.core.architecture import CourseArchitecture
    from evans.core.tf_utils import second_order
    from evans.ui.mainwindow import MainWindow
    window = MainWindow(CourseArchitecture(G=second_order(1.0, 0.5, 2.0)))
    yield window
    window.hide()


def test_nothing_unsaved_at_start(win):
    assert win.recovery_items() == []


def test_window_collects_and_restores_each_kind(win, tmp_path, monkeypatch):
    editor, live, sim = win._console.editor, win._console.live, win._sim_tab
    document = editor.new_document()
    document.code.insertPlainText("K = 3;")      # as typing does
    live._widgets[0].editor.setPlainText("z = 7")
    sim._canvas.root_model().settings["StopTime"] = 42.0
    kinds = {i.kind for i in win.recovery_items()}
    assert kinds == {SCRIPT, LIVE, MODEL}

    # This window's session crashes with those in its folder.
    crashed = RecoveryStore(tmp_path, pid=999_999, started=1.0)
    crashed.begin()
    crashed.write(win.recovery_items())

    # Saved since, in effect: the window is back to clean.
    document.code.document().setModified(False)
    live.mark_saved()
    sim.mark_saved()
    assert win.recovery_items() == []

    monkeypatch.setattr(recovery, "process_alive", _never_alive)
    monkeypatch.setattr(win, "_ask_recovery", lambda items: "restore")
    win.start_recovery(root=tmp_path)
    try:
        assert not crashed.folder.exists()        # restored, then removed
        restored = {i.kind: i.text for i in win.recovery_items()}
        assert "K = 3;" in restored[SCRIPT]
        assert "z = 7" in restored[LIVE]
        assert json.loads(restored[MODEL])["settings"]["StopTime"] == 42.0
        # Its own folder is running and writes them on a tick.
        assert win._recovery.snapshot() == 3
        assert (win._recovery.store.folder / recovery.MANIFEST).exists()
    finally:
        win._recovery.stop()
    assert not win._recovery.store.folder.exists()


def test_later_keeps_and_discard_removes(win, tmp_path, monkeypatch):
    crashed = RecoveryStore(tmp_path, pid=999_998, started=1.0)
    crashed.begin()
    crashed.write([Item(SCRIPT, "script-1", "Untitled 1", "x")])
    monkeypatch.setattr(recovery, "process_alive", _never_alive)
    left = recovery.orphans(tmp_path)
    monkeypatch.setattr(win, "_ask_recovery", lambda items: "later")
    assert win.offer_recovery(left) == "later"
    assert crashed.folder.exists()
    monkeypatch.setattr(win, "_ask_recovery", lambda items: "discard")
    assert win.offer_recovery(left) == "discard"
    assert not crashed.folder.exists()


def test_autosave_menu_turns_it_off_and_on(win, tmp_path):
    win.start_recovery(root=tmp_path)
    try:
        assert win._recovery.running
        win._act_autosave.setChecked(False)
        assert not win._recovery.running
        assert not recovery.saved_enabled()
        win._autosave_interval_actions[300].trigger()
        assert recovery.saved_interval() == 300
        win._act_autosave.setChecked(True)
        assert win._recovery.running
        assert win._recovery.interval == 300
    finally:
        win._recovery.stop()
        recovery.remember(True, recovery.DEFAULT_INTERVAL)
