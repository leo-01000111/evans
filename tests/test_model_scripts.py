"""
Model scripts: the ``.m`` files a model runs on open and before each run.

Qt-free: the file field, paths, run order and stopping, the trust rule,
Simulink's PreLoadFcn/InitFcn through set_param/get_param, and what the
console's load_system and sim do with them. The Model tab and its dialog are
in ``tests/golden/test_model_scripts_ui.py``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from evans.console import Interpreter, matlab_runtime, set_figure_sink  # noqa: F401
from evans.console.figures import recording_sink
from evans.sim.blocks import by_category  # noqa: F401  (registers library)
from evans.sim.model import SimModel
from evans.sim.scripts import (
    BEFORE_RUN,
    ON_OPEN,
    ModelScript,
    ScriptError,
    callback_text,
    needs_trust,
    parse_callback,
    path_key,
    resolve,
    run_scripts,
    set_callback,
    stored_path,
)


def gain_model(name: str = "m") -> SimModel:
    """A step through a gain of ``Kp`` into 1/(s+1)."""
    m = SimModel(name)
    m.add("Step", "r", step_time=0.0)
    m.add("Gain", "K", gain="Kp")
    m.add("TransferFcn", "G", num="1", den="1, 1")
    m.connect("r", "K")
    m.connect("K", "G")
    return m


def write(folder: Path, name: str, text: str) -> Path:
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# ── the file field ──────────────────────────────────────────────

def test_scripts_round_trip_through_the_file(tmp_path):
    m = gain_model()
    m.scripts = [ModelScript("setup.m", True, True),
                 ModelScript("lib/gains.m", False, True),
                 ModelScript("only_listed.m")]
    m.save(tmp_path / "m.evx")
    again = SimModel.load(tmp_path / "m.evx")
    assert again.scripts == m.scripts
    assert again.path == tmp_path / "m.evx"
    assert again.to_dict() == m.to_dict()


def test_a_model_without_scripts_writes_no_field(tmp_path):
    m = gain_model()
    assert "scripts" not in m.to_dict()
    m.save(tmp_path / "m.evx")
    data = json.loads((tmp_path / "m.evx").read_text(encoding="utf-8"))
    assert "scripts" not in data


def test_a_file_without_the_field_loads_with_no_scripts(tmp_path):
    data = gain_model().to_dict()
    assert "scripts" not in data
    path = tmp_path / "old.evx"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert SimModel.load(path).scripts == []


def test_bad_entries_are_dropped_not_fatal(tmp_path):
    data = gain_model().to_dict()
    data["scripts"] = [{"path": "ok.m", "before_run": True}, {"path": ""},
                       "nonsense", {"on_open": True}]
    path = tmp_path / "odd.evx"
    path.write_text(json.dumps(data), encoding="utf-8")
    assert SimModel.load(path).scripts == [ModelScript("ok.m", False, True)]


def test_copy_keeps_scripts_and_path(tmp_path):
    m = gain_model()
    m.scripts = [ModelScript("a.m", True)]
    m.save(tmp_path / "m.evx")
    c = m.copy()
    assert c.scripts == m.scripts and c.scripts[0] is not m.scripts[0]
    assert c.path == m.path


# ── paths ───────────────────────────────────────────────────────

def test_paths_are_stored_relative_to_the_model(tmp_path):
    model = tmp_path / "models" / "m.evx"
    assert stored_path(tmp_path / "models" / "setup.m", model) == "setup.m"
    assert stored_path(tmp_path / "scripts" / "s.m", model) == "../scripts/s.m"
    # No model file yet: absolute.
    absolute = stored_path(tmp_path / "s.m", None)
    assert Path(absolute).is_absolute()


def test_resolve_looks_beside_the_model_then_the_search_folders(tmp_path):
    write(tmp_path / "models", "setup.m", "")
    write(tmp_path / "elsewhere", "other.m", "")
    model = tmp_path / "models" / "m.evx"
    assert resolve("setup.m", model) == tmp_path / "models" / "setup.m"
    assert resolve("other.m", model) is None
    assert resolve("other.m", model, [tmp_path / "elsewhere"]) == \
        tmp_path / "elsewhere" / "other.m"
    absolute = str(tmp_path / "elsewhere" / "other.m")
    assert resolve(absolute, None) == Path(absolute)


def test_save_as_elsewhere_keeps_relative_scripts_pointing_at_their_files(
        tmp_path):
    write(tmp_path / "a", "setup.m", "")
    m = gain_model()
    m.scripts = [ModelScript("setup.m", True), ModelScript("gone.m", True)]
    m.save(tmp_path / "a" / "m.evx")
    (tmp_path / "b" / "deeper").mkdir(parents=True)
    m.save(tmp_path / "b" / "deeper" / "m2.evx")
    assert m.scripts[0].path == "../../a/setup.m"
    assert resolve(m.scripts[0], m.path) == tmp_path / "a" / "setup.m"
    assert m.scripts[1].path == "gone.m"           # not found: left alone


# ── running ─────────────────────────────────────────────────────

class Recorder:
    """A ``run_one`` that records the order and fails on request."""

    def __init__(self, failing=()) -> None:
        self.ran: list[str] = []
        self.failing = set(failing)

    def __call__(self, path: Path, script: ModelScript):
        self.ran.append(path.name)
        if path.name in self.failing:
            return "it broke", 2
        return None


def test_scripts_run_in_order_and_only_when_ticked(tmp_path):
    for name in ("a.m", "b.m", "c.m"):
        write(tmp_path, name, "")
    scripts = [ModelScript("c.m", True, True), ModelScript("a.m", False, True),
               ModelScript("b.m", True, False)]
    model = tmp_path / "m.evx"
    rec = Recorder()
    assert run_scripts(scripts, ON_OPEN, rec, model_path=model) == 2
    assert rec.ran == ["c.m", "b.m"]
    rec = Recorder()
    run_scripts(scripts, BEFORE_RUN, rec, model_path=model)
    assert rec.ran == ["c.m", "a.m"]


def test_an_error_before_a_run_stops_it_and_names_the_script(tmp_path):
    for name in ("a.m", "b.m", "c.m"):
        write(tmp_path, name, "")
    scripts = [ModelScript(n, before_run=True) for n in ("a.m", "b.m", "c.m")]
    rec = Recorder(failing={"b.m"})
    with pytest.raises(ScriptError) as info:
        run_scripts(scripts, BEFORE_RUN, rec, model_path=tmp_path / "m.evx")
    assert rec.ran == ["a.m", "b.m"]               # c never ran
    assert info.value.script == "b.m" and info.value.line == 2
    assert "b.m, line 2: it broke" in str(info.value)


def test_an_error_on_open_does_not_stop_the_rest(tmp_path):
    for name in ("a.m", "b.m"):
        write(tmp_path, name, "")
    scripts = [ModelScript(n, on_open=True) for n in ("a.m", "b.m")]
    rec = Recorder(failing={"a.m"})
    run_scripts(scripts, ON_OPEN, rec, model_path=tmp_path / "m.evx")
    assert rec.ran == ["a.m", "b.m"]


def test_a_missing_script_on_open_is_a_warning_naming_it(tmp_path):
    write(tmp_path, "b.m", "")
    scripts = [ModelScript("sub/gone.m", on_open=True),
               ModelScript("b.m", on_open=True)]
    warnings: list[str] = []
    rec = Recorder()
    run_scripts(scripts, ON_OPEN, rec, model_path=tmp_path / "m.evx",
                warn=warnings.append)
    assert rec.ran == ["b.m"]
    assert len(warnings) == 1 and "gone.m" in warnings[0]


def test_a_missing_script_before_a_run_stops_it(tmp_path):
    scripts = [ModelScript("gone.m", before_run=True)]
    with pytest.raises(ScriptError, match="gone.m"):
        run_scripts(scripts, BEFORE_RUN, Recorder(),
                    model_path=tmp_path / "m.evx")


# ── trust ───────────────────────────────────────────────────────

def test_trust_is_asked_only_for_an_untrusted_file_with_scripts(tmp_path):
    path = tmp_path / "m.evx"
    with_scripts = [ModelScript("s.m", True, False)]
    assert needs_trust(with_scripts, ON_OPEN, path, [])
    # Nothing due then: nothing to ask about.
    assert not needs_trust(with_scripts, BEFORE_RUN, path, [])
    assert not needs_trust([], ON_OPEN, path, [])
    # Built in this session: the user's own.
    assert not needs_trust(with_scripts, ON_OPEN, None, [])
    # Trusted, however the path was spelled.
    assert not needs_trust(with_scripts, ON_OPEN, path, [path_key(path)])
    other = tmp_path / "x" / ".." / "m.evx"
    assert not needs_trust(with_scripts, ON_OPEN, other, [path_key(path)])
    assert needs_trust(with_scripts, ON_OPEN, tmp_path / "n.evx",
                       [path_key(path)])


# ── Simulink's callbacks ────────────────────────────────────────

def test_parse_callback_takes_script_names_and_refuses_code():
    assert parse_callback("setup") == ["setup.m"]
    assert parse_callback("params.m; gains, setup\n") == \
        ["params.m", "gains.m", "setup.m"]
    assert parse_callback("  ") == []
    assert parse_callback("a; a") == ["a.m"]
    for code in ("Kp = 2;", "disp('x')", "run(x)"):
        with pytest.raises(ValueError, match="not code"):
            parse_callback(code)


def test_set_callback_edits_one_flag_and_keeps_the_other():
    scripts = [ModelScript("a.m", True, False), ModelScript("b.m", True, True)]
    set_callback(scripts, BEFORE_RUN, "a; c")
    assert scripts == [ModelScript("a.m", True, True),
                       ModelScript("c.m", False, True),
                       ModelScript("b.m", True, False)]
    assert callback_text(scripts, BEFORE_RUN) == "a; c"
    assert callback_text(scripts, ON_OPEN) == "a; b"
    # Cleared: b keeps its on-open tick, c had only this one and goes.
    set_callback(scripts, BEFORE_RUN, "")
    assert scripts == [ModelScript("a.m", True, False),
                       ModelScript("b.m", True, False)]


def test_set_callback_takes_the_order_given():
    scripts = [ModelScript("a.m", False, True), ModelScript("b.m", False, True)]
    set_callback(scripts, BEFORE_RUN, "b; a")
    assert [s.path for s in scripts] == ["b.m", "a.m"]


def test_callback_text_keeps_folders_as_written():
    scripts = [ModelScript("../lib/setup.m", True)]
    assert callback_text(scripts, ON_OPEN) == "../lib/setup.m"


# ── the console ─────────────────────────────────────────────────

@pytest.fixture
def it(tmp_path, monkeypatch):
    previous = set_figure_sink(recording_sink())
    monkeypatch.chdir(tmp_path)
    yield Interpreter()
    set_figure_sink(previous)


def command(it, source: str):
    return it.command(source)


def ok(it, source: str) -> str:
    result = it.command(source)
    assert not result.error, f"{source!r} → {result.error}"
    return result.output


def test_set_param_and_get_param_map_onto_the_scripts(it, tmp_path):
    gain_model("m").save(tmp_path / "m.evx")
    ok(it, "set_param('m', 'InitFcn', 'setup; gains', 'PreLoadFcn', 'setup')")
    assert it.evaluate("get_param('m', 'InitFcn')") == "setup; gains"
    assert it.evaluate("get_param('m', 'PreLoadFcn')") == "setup"
    model = it._matlab_runtime().models["m"]
    assert model.scripts == [ModelScript("setup.m", True, True),
                             ModelScript("gains.m", False, True)]
    error = command(it, "set_param('m', 'InitFcn', 'Kp = 2;')").error
    assert "not code" in error


def test_sim_runs_the_init_scripts_in_order_first(it, tmp_path):
    write(tmp_path, "first.m", "Kp = 1; trail = 'first';\n")
    write(tmp_path, "second.m", "Kp = Kp * 3; trail = [trail ' second'];\n")
    gain_model("m").save(tmp_path / "m.evx")
    ok(it, "set_param('m', 'InitFcn', 'first; second', 'StopTime', '20')")
    ok(it, "out = sim('m');")
    assert it.evaluate("trail") == "first second"
    assert it.evaluate("Kp") == 3
    assert it.evaluate("out.tout(end)") == pytest.approx(20.0)


def test_an_init_script_error_stops_sim_and_says_which(it, tmp_path):
    write(tmp_path, "good.m", "Kp = 2; reached = 1;\n")
    write(tmp_path, "broken.m", "a = 1;\nb = no_such_thing + 1;\n")
    write(tmp_path, "after.m", "after_ran = 1;\n")
    gain_model("m").save(tmp_path / "m.evx")
    ok(it, "set_param('m', 'InitFcn', 'good; broken; after')")
    error = command(it, "out = sim('m');").error
    assert "broken.m, line 2" in error and "no_such_thing" in error
    assert "run stopped" in error
    assert it.evaluate("reached") == 1
    assert command(it, "after_ran").error            # never ran
    assert command(it, "out").error                  # no result either


def test_load_system_runs_the_preload_scripts(it, tmp_path):
    write(tmp_path, "setup.m", "Kp = 5;\ndisp('setup here')\n")
    m = gain_model("m")
    m.scripts = [ModelScript("setup.m", on_open=True)]
    m.save(tmp_path / "m.evx")
    out = ok(it, "load_system('m')")
    assert "setup here" in out
    assert it.evaluate("Kp") == 5


def test_load_system_reports_a_missing_or_failing_script_and_loads(
        it, tmp_path):
    write(tmp_path, "fails.m", "x = 1;\ny = nope;\n")
    m = gain_model("m")
    m.scripts = [ModelScript("gone.m", on_open=True),
                 ModelScript("fails.m", on_open=True)]
    m.save(tmp_path / "m.evx")
    out = ok(it, "load_system('m')")
    assert "gone.m was not found" in out
    assert "Error in model script fails.m, line 2" in out
    assert "m" in it._matlab_runtime().models


def test_the_scripts_fixture_loads_and_runs(it):
    fixtures = Path(__file__).resolve().parent / "fixtures" / "models"
    model = SimModel.load(fixtures / "model_scripts.evx")
    assert model.scripts == [
        ModelScript("model_scripts_setup.m", True, True),
        ModelScript("gone/missing.m", True, False)]
    out = ok(it, f"load_system('{(fixtures / 'model_scripts.evx').as_posix()}')")
    assert "missing.m was not found" in out
    assert it.evaluate("Kp") == 4
