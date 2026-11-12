"""
Old model files keep opening: the stability promise, kept checkable.

``tests/fixtures/models/`` holds real model files from past versions. They
were taken from git history, not written by hand, except where noted:

* ``<example>_v0.12.fmdl``: the four examples as 0.12.1 shipped them, the
  first release with examples. They were unchanged through 0.19.0, the last
  release that wrote ``.fmdl``.
* ``legacy_faux_minimal.fmdl``: the smallest file the reader accepts in the
  pre-0.9 format (the old program's format tag, no ``version`` key). No such
  file exists in git history, so it is built by hand to match what that
  format's reader accepted.
* ``model_scripts.evx`` (with ``model_scripts_setup.m``): the first file with
  model scripts, one that exists and one that does not. Written by the
  version that added them.

THE FIXTURES MUST NEVER BE EDITED OR DELETED WITHIN 1.x. When the format
changes, add fixtures for the new format and keep the old ones loading.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from evans.examples import EXAMPLES
from evans.sim.blocks import by_category  # noqa: F401  (registers library)
from evans.sim.compile import compile_model
from evans.sim.model import FORMAT, LEGACY_FORMATS, VERSION, ModelError, SimModel
from evans.sim.solver import simulate

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "models"
OLD_FILES = sorted(FIXTURES.glob("*.fmdl"))
STEMS = [Path(e.file).stem for e in EXAMPLES]


def _run(model: SimModel):
    return simulate(model, t_end=float(model.settings["StopTime"]),
                    n_points=400)


def test_the_fixtures_are_there():
    names = {p.name for p in OLD_FILES}
    assert {f"{s}_v0.12.fmdl" for s in STEMS} <= names
    assert "legacy_faux_minimal.fmdl" in names


def test_each_format_tag_has_a_fixture():
    tags = {json.loads(p.read_text(encoding="utf-8"))["format"]
            for p in OLD_FILES}
    assert tags == {FORMAT, *LEGACY_FORMATS}


@pytest.mark.parametrize("path", OLD_FILES, ids=lambda p: p.name)
def test_every_old_file_loads_compiles_and_simulates(path):
    model = SimModel.load(path)
    compile_model(model)
    result = _run(model)
    assert len(result.t) > 1
    assert result.signals
    assert all(np.all(np.isfinite(v)) for v in result.signals.values())


@pytest.mark.parametrize("stem", STEMS)
def test_an_old_example_simulates_like_the_current_one(stem):
    old = SimModel.load(FIXTURES / f"{stem}_v0.12.fmdl")
    new = SimModel.load(next(e.path for e in EXAMPLES
                             if Path(e.file).stem == stem))
    a, b = _run(old), _run(new)
    assert set(a.signals) == set(b.signals)
    np.testing.assert_allclose(a.t, b.t, rtol=1e-12, atol=1e-12)
    for key in a.signals:
        np.testing.assert_allclose(a.signals[key], b.signals[key],
                                   rtol=1e-9, atol=1e-9, err_msg=key)


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e: e.file)
@pytest.mark.parametrize("suffix", [".evx", ".fmdl"])
def test_every_example_round_trips(example, suffix, tmp_path):
    model = SimModel.load(example.path)
    path = tmp_path / f"copy{suffix}"
    model.save(path)
    again = SimModel.load(path)
    assert again.to_dict() == {**model.to_dict(), "name": "copy"}
    # A second pass changes nothing either.
    path2 = tmp_path / f"copy2{suffix}"
    again.save(path2)
    assert SimModel.load(path2).to_dict() == {**again.to_dict(), "name": "copy2"}


def test_old_files_open_with_no_scripts():
    for path in OLD_FILES:
        assert SimModel.load(path).scripts == [], path.name


def test_the_scripts_fixture_keeps_loading_and_running():
    from evans.console import Interpreter
    from evans.sim.scripts import ModelScript

    model = SimModel.load(FIXTURES / "model_scripts.evx")
    assert model.scripts == [
        ModelScript("model_scripts_setup.m", on_open=True, before_run=True),
        ModelScript("gone/missing.m", on_open=True, before_run=False)]
    # What its script sets, the blocks read.
    it = Interpreter()
    it.run_script((FIXTURES / "model_scripts_setup.m").read_text(
        encoding="utf-8"), "matlab")
    result = simulate(model, t_end=float(model.settings["StopTime"]),
                      n_points=400, evaluate=it.evaluate)
    np.testing.assert_allclose(result.trace("G")[-1],
                               4 * (1 - np.exp(-5.0)), rtol=1e-3)


def test_a_newer_format_version_is_refused_with_a_message(tmp_path):
    data = SimModel.load(FIXTURES / "dc_motor_v0.12.fmdl").to_dict()
    data["version"] = VERSION + 1
    path = tmp_path / "future.evx"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ModelError, match="newer version"):
        SimModel.load(path)


def test_a_file_of_another_format_is_refused(tmp_path):
    path = tmp_path / "other.evx"
    path.write_text(json.dumps({"format": "something-else"}),
                    encoding="utf-8")
    with pytest.raises(ModelError, match="not an Evans model file"):
        SimModel.load(path)
