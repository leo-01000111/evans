"""
The model file's extension moved from ``.fmdl`` to ``.evx``.

Old files keep opening for good; the first plain Save of one offers the new
format once, and either answer leaves the old file exactly as it was.
Lookups by name prefer ``.evx``. Autosave is not touched by any of this.
"""

from __future__ import annotations

import os

import pytest

pytest.importorskip("PySide6", reason="Qt not available")

from PySide6.QtWidgets import QApplication, QFileDialog

from evans.console import Interpreter, matlab_runtime  # noqa: F401
from evans.examples import EXAMPLES
from evans.sim.model import (
    LEGACY_SUFFIX,
    SUFFIX,
    SimModel,
    find_model_file,
    is_model_file,
    preferred_file,
)
from evans.ui.persist import RecentFiles
from evans.ui.sim.sim_tab import SimTab


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def tab(app):
    widget = SimTab()
    yield widget
    widget.deleteLater()


def _model(name="loop", gain=2.0) -> SimModel:
    m = SimModel(name)
    m.add("Step", "r")
    m.add("Gain", "k", gain=gain)
    m.connect("r", "k")
    return m


def _old_file(tmp_path, name="loop"):
    path = tmp_path / f"{name}{LEGACY_SUFFIX}"
    _model(name).save(path)
    return path, path.read_bytes()


def _no_save_dialog(monkeypatch):
    def fail(*_a, **_k):
        raise AssertionError("Save must not ask where")
    monkeypatch.setattr(QFileDialog, "getSaveFileName", fail)


def _answers(monkeypatch, tab, *replies):
    asked = []

    def ask():
        asked.append(True)
        return replies[len(asked) - 1]
    monkeypatch.setattr(tab, "ask_new_format", ask)
    return asked


# ── the file format ─────────────────────────────────────────────

def test_the_extensions():
    assert SUFFIX == ".evx" and LEGACY_SUFFIX == ".fmdl"
    assert is_model_file("a/b.EVX") and is_model_file("b.fmdl")
    assert not is_model_file("b.m")


def test_an_old_file_opens_and_its_content_matches_a_new_one(tmp_path):
    old, _ = _old_file(tmp_path)
    data = SimModel.load(old).to_dict()
    assert data["format"] == "evans-model" and data["version"] >= 1
    new = tmp_path / "loop.evx"
    SimModel.load(old).save(new)
    assert SimModel.load(new).to_dict() == data


def test_save_leaves_no_partial_file(tmp_path):
    _model().save(tmp_path / "m.evx")
    assert os.listdir(tmp_path) == ["m.evx"]


def test_a_failed_save_leaves_the_old_file_whole(tmp_path, monkeypatch):
    path = tmp_path / "m.evx"
    _model(gain=1.0).save(path)
    before = path.read_bytes()

    def broken(*_a, **_k):
        raise OSError("disk full")
    monkeypatch.setattr(os, "replace", broken)
    with pytest.raises(OSError):
        _model(gain=5.0).save(path)
    assert path.read_bytes() == before
    assert os.listdir(tmp_path) == ["m.evx"]


def test_lookup_prefers_evx(tmp_path):
    assert find_model_file(tmp_path, "loop") is None
    _old_file(tmp_path)
    assert find_model_file(tmp_path, "loop").suffix == ".fmdl"
    _model().save(tmp_path / "loop.evx")
    assert find_model_file(tmp_path, "loop").suffix == ".evx"


def test_a_recent_fmdl_opens_its_newer_evx(tmp_path):
    old, _ = _old_file(tmp_path)
    assert preferred_file(old) == old
    new = tmp_path / "loop.evx"
    _model().save(new)
    os.utime(new, (old.stat().st_mtime + 5,) * 2)
    assert preferred_file(old) == new
    # A .fmdl saved later on purpose (for an older Evans) is the newer one.
    os.utime(old, (new.stat().st_mtime + 5,) * 2)
    assert preferred_file(old) == old
    assert preferred_file(new) == new


def test_recent_files_take_both():
    assert {".evx", ".fmdl"} <= set(RecentFiles.SUFFIXES)


def test_the_examples_are_evx():
    assert EXAMPLES and all(e.file.endswith(".evx") and e.path.is_file()
                            for e in EXAMPLES)
    assert not list(EXAMPLES[0].path.parent.glob("*.fmdl"))


# ── the console ─────────────────────────────────────────────────

def _run(it, source, folder):
    results = it.run_script(source, "matlab", folder=str(folder))
    failed = [r for r in results if r.error]
    assert not failed, failed[0].error


def test_the_console_reads_old_files_and_prefers_new_ones(tmp_path):
    it = Interpreter()
    _old_file(tmp_path)
    _run(it, "load_system('loop'); g = get_param('loop/k', 'Gain');",
         tmp_path)
    assert str(it.namespace["g"]) == "2"
    _model(gain=7.0).save(tmp_path / "loop.evx")
    _run(it, "close_system('loop'); load_system('loop'); "
             "g = get_param('loop/k', 'Gain');", tmp_path)
    assert str(it.namespace["g"]) == "7"


def test_save_system_writes_evx_unless_fmdl_is_asked_for(tmp_path):
    it = Interpreter()
    _run(it, "new_system('a'); save_system('a'); "
             "new_system('b'); save_system('b', 'b.fmdl');", tmp_path)
    assert (tmp_path / "a.evx").is_file()
    assert (tmp_path / "b.fmdl").is_file()
    assert not (tmp_path / "b.fmdl.evx").exists()


# ── the Model tab's Save ────────────────────────────────────────

def test_keep_fmdl_saves_in_place_and_asks_once(tab, tmp_path, monkeypatch):
    old, _ = _old_file(tmp_path)
    tab.load_model(old)
    assert tab.model_path == old
    asked = _answers(monkeypatch, tab, False)
    _no_save_dialog(monkeypatch)
    tab._canvas.root_model().blocks["k"].params["gain"] = 3.0
    tab.save_model()
    tab.save_model()
    assert len(asked) == 1
    assert tab.model_path == old
    assert not (tmp_path / "loop.evx").exists()
    assert SimModel.load(old).blocks["k"].params["gain"] == 3.0


def test_save_as_evx_writes_beside_and_leaves_the_original(
        tab, tmp_path, monkeypatch):
    old, before = _old_file(tmp_path)
    tab.load_model(old)
    asked = _answers(monkeypatch, tab, True)
    _no_save_dialog(monkeypatch)
    used = []
    tab.file_used.connect(used.append)
    tab._canvas.root_model().blocks["k"].params["gain"] = 4.0
    tab.save_model()
    new = tmp_path / "loop.evx"
    assert old.read_bytes() == before                # untouched
    assert SimModel.load(new).blocks["k"].params["gain"] == 4.0
    assert tab.model_path == new and used == [new]
    tab.save_model()                                 # an .evx: never asked
    assert len(asked) == 1
    assert old.read_bytes() == before


def test_an_existing_evx_is_not_overwritten_unasked(tab, tmp_path, monkeypatch):
    old, _ = _old_file(tmp_path)
    theirs = tmp_path / "loop.evx"
    theirs.write_text("someone else's", encoding="utf-8")
    tab.load_model(old)
    _answers(monkeypatch, tab, True)
    starts = []

    def dialog(_parent, _title, start, _filters):
        starts.append(start)
        return "", ""                                 # cancelled
    monkeypatch.setattr(QFileDialog, "getSaveFileName", dialog)
    tab.save_model()
    assert starts == [str(theirs)]
    assert theirs.read_text(encoding="utf-8") == "someone else's"


def test_an_evx_file_never_sees_the_prompt(tab, tmp_path, monkeypatch):
    path = tmp_path / "m.evx"
    _model("m").save(path)
    tab.load_model(path)
    asked = _answers(monkeypatch, tab)
    _no_save_dialog(monkeypatch)
    tab.save_model()
    assert not asked


def test_save_without_a_file_asks_where_and_offers_both(
        tab, tmp_path, monkeypatch):
    seen = []

    def dialog(_parent, _title, start, filters):
        seen.append((start, filters))
        return str(tmp_path / "fresh"), filters.split(";;")[0]
    monkeypatch.setattr(QFileDialog, "getSaveFileName", dialog)
    assert tab.model_path is None                    # the starter model
    tab.save_model()
    (start, filters), = seen
    assert start.endswith(".evx")
    assert "*.evx" in filters and "*.fmdl" in filters
    assert (tmp_path / "fresh.evx").is_file()
    assert tab.model_path == tmp_path / "fresh.evx"


def test_save_as_fmdl_for_an_older_evans(tab, tmp_path, monkeypatch):
    def dialog(_parent, _title, _start, filters):
        return str(tmp_path / "copy"), filters.split(";;")[1]
    monkeypatch.setattr(QFileDialog, "getSaveFileName", dialog)
    tab.save_model_as()
    assert tab.model_path == tmp_path / "copy.fmdl"
    asked = _answers(monkeypatch, tab)
    _no_save_dialog(monkeypatch)
    tab.save_model()                                 # chosen on purpose
    assert not asked


def test_an_example_or_another_model_has_no_file(tab, monkeypatch):
    tab.load_model(EXAMPLES[0].path, remember=False)
    assert tab.model_path is None
    tab.load_model(EXAMPLES[0].path)
    assert tab.model_path == EXAMPLES[0].path
    tab._canvas.set_model(_model())                  # e.g. from open_system
    assert tab.model_path is None


def test_autosave_never_writes_a_model_file(tab, tmp_path):
    old, before = _old_file(tmp_path)
    tab.load_model(old)
    tab._canvas.root_model().blocks["k"].params["gain"] = 9.0
    items = tab.recovery_items()
    assert items and items[0].kind == "model"
    assert sorted(os.listdir(tmp_path)) == ["loop.fmdl"]
    assert old.read_bytes() == before
