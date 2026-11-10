"""
Editing the diagram and getting things out of it: rotate and flip, notes,
signal names, wire bends, Create Subsystem from Selection, diagram and data
export, comparing runs, the example models, and the Model tab's run reaching
the console.
"""

from __future__ import annotations

import csv
import math

import numpy as np
import pytest
from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

from evans.examples import EXAMPLES, examples
from evans.sim import SimModel, simulate
from evans.sim.edit import group_into_subsystem, ungroup_subsystem
from evans.sim.export import export_signals, mat_name
from evans.sim.model import ModelError, PortRef
from evans.ui.sim.canvas import SimCanvas
from evans.ui.sim.items import AnnotationItem, BlockItem, WireItem, route
from evans.ui.sim.scope import ScopeWidget


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def loop() -> SimModel:
    m = SimModel("loop")
    m.add("Step", "r", x=0, y=0, step_time=0.0)
    m.add("Sum", "e", x=200, y=0, signs="+-")
    m.add("Gain", "K", x=400, y=0, gain=4.0)
    m.add("TransferFcn", "G", x=600, y=0, num="1", den="1, 1")
    m.connect("r", "e.in1")
    m.connect("e", "K")
    m.connect("K", "G")
    m.connect("G", "e.in2")
    return m


@pytest.fixture
def canvas(app):
    view = SimCanvas(loop())
    yield view
    view.deleteLater()


def select(canvas, *ids):
    canvas.scene().clearSelection()
    for bid in ids:
        canvas._blocks[bid].setSelected(True)


# ──────────────────────────────────────────────────────────────
#  The model keeps what the editor does
# ──────────────────────────────────────────────────────────────

def test_orientation_notes_names_and_bends_round_trip(tmp_path):
    m = loop()
    m.orient("K", rotation=90, flip=True)
    m.annotations.append({"text": "a note", "x": 10.0, "y": -50.0})
    m.signal_names["G.out"] = "y"
    conn = m.connection_into(m.connections[1].dst)
    m.bends[str(conn)] = 330.0
    m.move("K", 420, 0)                     # moving keeps the orientation
    path = tmp_path / "m.fmdl"
    m.save(path)
    back = SimModel.load(path)
    place = back.placement("K")
    assert (place.x, place.rotation, place.flip) == (420, 90, True)
    assert back.annotations == [{"text": "a note", "x": 10.0, "y": -50.0}]
    assert back.signal_names == {"G.out": "y"}
    assert back.bends == {str(conn): 330.0}


def test_removing_a_block_drops_its_name_and_bends():
    m = loop()
    m.signal_names["K.out"] = "u"
    m.bends["K.out → G.in"] = 500.0
    m.remove("K")
    assert m.signal_names == {} and m.bends == {}


def test_an_unturned_model_saves_as_before():
    entry = loop().to_dict()["blocks"][0]
    assert "rotation" not in entry and "flip" not in entry


# ──────────────────────────────────────────────────────────────
#  Create subsystem from selection
# ──────────────────────────────────────────────────────────────

def test_grouping_keeps_what_the_model_computes():
    before = simulate(loop(), t_end=5.0, n_points=50).trace("G.out")
    m = loop()
    sub = group_into_subsystem(m, ["K", "G"], "plant")
    assert m.block(sub).inputs == ["in1"] and m.block(sub).outputs == ["out1"]
    after = simulate(m, t_end=5.0, n_points=50).trace("plant/G.out")
    assert np.allclose(before, after)
    # 4/(s+5) closed loop: 0.8·(1 − e^{−5t}).
    assert after[-1] == pytest.approx(0.8 * (1 - math.exp(-25)), rel=1e-5)


def test_a_signal_entering_twice_gets_one_inport():
    m = SimModel("fan")
    m.add("Step", "r", step_time=0.0)
    m.add("Gain", "a", gain=1.0)
    m.add("Gain", "b", gain=2.0)
    m.add("Sum", "s", signs="++")
    m.connect("r", "a")
    m.connect("r", "b")
    m.connect("a", "s.in1")
    m.connect("b", "s.in2")
    sub = group_into_subsystem(m, ["a", "b", "s"])
    assert m.block(sub).inputs == ["in1"]
    assert simulate(m, t_end=1.0).trace(f"{sub}/s.out")[-1] == 3.0


def test_create_subsystem_on_the_canvas_is_one_undo_step(canvas):
    select(canvas, "K", "G")
    sub = canvas.create_subsystem("plant")
    assert sub == "plant" and "K" not in canvas.model.blocks
    canvas.undo_stack.undo()
    assert {"K", "G"} <= set(canvas.model.blocks)
    assert "plant" not in canvas.model.blocks


# ──────────────────────────────────────────────────────────────
#  Ungroup / expand subsystem
# ──────────────────────────────────────────────────────────────

def test_group_then_ungroup_gives_the_same_simulation():
    before = simulate(loop(), t_end=5.0, n_points=50).trace("G.out")
    m = loop()
    sub = group_into_subsystem(m, ["K", "G"], "plant")
    ids = ungroup_subsystem(m, sub)
    assert sorted(ids) == ["G", "K"] and sub not in m.blocks
    assert {str(c) for c in m.connections} == {
        str(c) for c in loop().connections}
    assert (m.placement("K").x, m.placement("G").x) == (400, 600)
    after = simulate(m, t_end=5.0, n_points=50).trace("G.out")
    assert np.allclose(after, before)


def test_ungroup_renames_clashes_and_leaves_nested_subsystems_alone():
    m = loop()
    inner = group_into_subsystem(m, ["K"], "k")
    outer = group_into_subsystem(m, [inner, "G"], "outer")
    ids = ungroup_subsystem(m, outer)
    assert sorted(ids) == ["G", "k"] and m.block("k").type_name == "Subsystem"
    assert m.block("k").inner_model().blocks.keys() >= {"K"}
    after = simulate(m, t_end=5.0, n_points=50).trace("G.out")
    assert after[-1] == pytest.approx(0.8 * (1 - math.exp(-25)), rel=1e-5)


def test_ungroup_suffixes_a_clashing_name():
    m = loop()
    sub = group_into_subsystem(m, ["K", "G"], "plant")
    m.add("Gain", "K", gain=1.0)
    ids = ungroup_subsystem(m, sub)
    assert sorted(ids) == ["G", "K2"] and m.block("K").params["gain"] == 1.0


def test_ungroup_joins_a_pass_through_and_keeps_a_signal_name():
    m = SimModel("p")
    m.add("Step", "r", step_time=0.0)
    m.add("Gain", "g", gain=2.0)
    m.add("Scope", "sc0")
    m.connect("r", "g")
    m.connect("g", "sc0")
    sub = group_into_subsystem(m, ["g"], "s")
    inner = m.block(sub).inner_model()
    inner.add("Outport", "Out2", port_name="out2", order=2)
    inner.connect("In1", "Out2")                    # in1 straight to out2
    m.block(sub).set_inner(inner)
    m.add("Scope", "sc")
    m.connect(f"{sub}.out2", "sc")
    m.signal_names[f"{sub}.out1"] = "y"
    ungroup_subsystem(m, sub)
    assert str(m.connection_into(PortRef("sc", "in1")).src) == "r.out"
    assert m.signal_names == {"g.out": "y"}


def test_ungroup_refuses_a_conditional_subsystem():
    m = SimModel("c")
    m.add("Step", "r", step_time=0.0)
    m.add("Gain", "g", gain=2.0)
    m.connect("r", "g")
    sub = group_into_subsystem(m, ["g"], "s")
    inner = m.block(sub).inner_model()
    inner.add("Enable", "En")
    m.block(sub).set_inner(inner)
    before = m.to_dict()
    with pytest.raises(ModelError, match="conditional"):
        ungroup_subsystem(m, sub)
    assert m.to_dict() == before


def test_expand_subsystem_on_the_canvas_is_one_undo_step(canvas):
    select(canvas, "K", "G")
    sub = canvas.create_subsystem("plant")
    canvas.undo_stack.clear()
    assert canvas.ungroup_subsystem(sub)
    assert {"K", "G"} <= set(canvas.model.blocks)
    assert sub not in canvas.model.blocks
    canvas.undo_stack.undo()
    assert sub in canvas.model.blocks and "K" not in canvas.model.blocks


# ──────────────────────────────────────────────────────────────
#  Rotate, flip, notes, names, bends on the canvas
# ──────────────────────────────────────────────────────────────

def test_rotate_turns_the_ports(canvas):
    item = canvas._blocks["K"]
    assert item.ports[("in", True)].direction == QPointF(-1, 0)
    select(canvas, "K")
    assert canvas.rotate_selection() == 1
    item = canvas._blocks["K"]
    assert canvas.model.placement("K").rotation == 90
    # A quarter turn clockwise: the input now faces up, the output down.
    assert item.ports[("in", True)].direction == QPointF(0, -1)
    assert item.ports[("out", False)].direction == QPointF(0, 1)
    w, h = item.size()
    assert w == item.height() and h == 110.0
    canvas.undo_stack.undo()
    assert canvas.model.placement("K").rotation == 0


def test_flip_puts_the_inputs_on_the_right(canvas):
    select(canvas, "G")
    canvas.flip_selection()
    item = canvas._blocks["G"]
    assert item.ports[("in", True)].pos().x() > 0
    assert item.ports[("out", False)].pos().x() < 0


def test_a_flipped_feedback_block_routes_without_crossing_itself():
    # Output on the left, facing left; the destination further left.
    path, axis = route(QPointF(0, 100), QPointF(-1, 0),
                       QPointF(-300, 0), QPointF(1, 0))
    assert axis == "x"
    xs = [path.elementAt(i).x for i in range(path.elementCount())]
    assert max(xs) <= 0 and min(xs) >= -300


def test_notes_are_added_edited_and_deleted(canvas):
    canvas.add_annotation(QPointF(100, -100), "the plant")
    assert canvas.model.annotations[0]["text"] == "the plant"
    notes = [i for i in canvas.scene().items()
             if isinstance(i, AnnotationItem)]
    assert len(notes) == 1 and notes[0].text == "the plant"
    canvas.edit_annotation(0, "the plant, 1/(s+1)")
    assert canvas.model.annotations[0]["text"] == "the plant, 1/(s+1)"
    canvas.scene().clearSelection()
    [i for i in canvas.scene().items()
     if isinstance(i, AnnotationItem)][0].setSelected(True)
    canvas.delete_selection()
    assert canvas.model.annotations == []
    canvas.undo_stack.undo()
    assert len(canvas.model.annotations) == 1


def test_a_signal_name_labels_every_branch(canvas):
    conn = next(c for c in canvas.model.connections if str(c.src) == "G.out")
    canvas.name_signal(conn, "y")
    labels = {w.label for w in canvas.scene().items()
              if isinstance(w, WireItem) and str(w.connection.src) == "G.out"}
    assert labels == {"y"}
    canvas.name_signal(conn, "")
    assert canvas.model.signal_names == {}


def test_dragging_a_bend_is_stored_and_undoable(canvas):
    wire = next(w for w in canvas._wires if str(w.connection.src) == "K.out")
    wire.bend_moved.emit(wire.connection, 470.0)
    assert canvas.model.bends[str(wire.connection)] == 470.0
    moved = next(w for w in canvas._wires if str(w.connection.src) == "K.out")
    xs = {round(moved._path.elementAt(i).x)
          for i in range(moved._path.elementCount())}
    assert 470 in xs
    canvas.undo_stack.undo()
    assert canvas.model.bends == {}


# ──────────────────────────────────────────────────────────────
#  Export
# ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("suffix, magic", [
    (".svg", b"<?xml"), (".pdf", b"%PDF"), (".png", b"\x89PNG"),
])
def test_the_diagram_exports(canvas, tmp_path, suffix, magic):
    path = tmp_path / f"diagram{suffix}"
    canvas.export_image(path)
    assert path.read_bytes()[:len(magic)] == magic


def test_exporting_keeps_the_selection(canvas, tmp_path):
    select(canvas, "K")
    canvas.export_image(tmp_path / "d.svg")
    assert canvas._blocks["K"].isSelected()


def test_signals_export_to_csv(tmp_path):
    result = simulate(loop(), t_end=1.0, n_points=11)
    path = export_signals(result, tmp_path / "s.csv", ["G.out", "r.out"])
    rows = list(csv.reader(path.open(encoding="utf-8")))
    assert rows[0] == ["t", "G.out", "r.out"]
    assert len(rows) == len(result.t) + 1
    assert float(rows[-1][1]) == pytest.approx(result.trace("G.out")[-1])


def test_signals_export_to_mat(tmp_path):
    from scipy.io import loadmat
    result = simulate(loop(), t_end=1.0, n_points=11)
    path = export_signals(result, tmp_path / "s.mat")
    data = loadmat(str(path))
    assert data["tout"].shape == (len(result.t), 1)
    assert np.allclose(data["G_out"][:, 0], result.trace("G.out"))
    assert mat_name("plant/G.out") == "plant_G_out"


def test_an_unknown_format_is_refused(tmp_path):
    result = simulate(loop(), t_end=1.0, n_points=5)
    with pytest.raises(ValueError, match=".csv or .mat"):
        export_signals(result, tmp_path / "s.xlsx")


# ──────────────────────────────────────────────────────────────
#  Comparing runs
# ──────────────────────────────────────────────────────────────

def test_the_scope_keeps_earlier_runs_and_draws_them(app):
    scope = ScopeWidget()
    for gain in (1.0, 2.0, 3.0):
        m = loop()
        m.block("K").set_param("gain", gain)
        scope.show_result(simulate(m, t_end=1.0, n_points=20))
    assert len(scope.history) == 2
    assert scope.history[0].trace("G.out")[-1] > \
        scope.history[1].trace("G.out")[-1]
    scope._compare.setChecked(True)
    scope._depth.setValue(2)
    names = [item.name() for item in scope._plot.getPlotItem().listDataItems()]
    assert "G.out (run −1)" in names and "G.out (run −2)" in names
    scope.clear()
    assert scope.history == []
    scope.deleteLater()


def test_the_scope_keeps_the_ticked_channels(app):
    scope = ScopeWidget()
    scope.show_result(simulate(loop(), t_end=1.0, n_points=10))
    for name, check in scope._checks.items():
        check.setChecked(name == "K.out")
    scope.show_result(simulate(loop(), t_end=1.0, n_points=10))
    ticked = [n for n, c in scope._checks.items() if c.isChecked()]
    assert ticked == ["K.out"]
    scope.deleteLater()


def test_the_scope_shows_an_xy_graph(app):
    m = SimModel("xy")
    m.add("Sine", "s")
    m.add("Clock", "c")
    m.add("XYGraph", "g", title="phase")
    m.connect("c", "g.x")
    m.connect("s", "g.y")
    scope = ScopeWidget()
    scope.show_result(simulate(m, t_end=1.0, n_points=10))
    assert scope._view.findText("phase") >= 0
    scope._view.setCurrentText("phase")
    assert len(scope._plot.getPlotItem().listDataItems()) == 1
    scope.deleteLater()


# ──────────────────────────────────────────────────────────────
#  Examples
# ──────────────────────────────────────────────────────────────

def test_every_example_is_installed():
    assert [e.file for e in examples()] == [e.file for e in EXAMPLES]


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda e: e.file)
def test_every_example_runs_as_it_opens(example):
    model = SimModel.load(example.path)
    assert model.name == example.path.stem
    result = simulate(model, t_end=float(model.settings["StopTime"]),
                      n_points=400)
    assert not [w for w in result.warnings if "unconnected" in w]


def test_the_examples_show_what_they_promise():
    by_file = {e.file: SimModel.load(e.path) for e in EXAMPLES}
    m = by_file["pid_saturation.evx"]
    r = simulate(m, t_end=20.0, n_points=400)
    # Windup overshoots well past the anti-windup loop.
    assert r.trace("G_w.out").max() > r.trace("G_a.out").max() + 0.1
    m = by_file["inverted_pendulum.evx"]
    r = simulate(m, t_end=5.0, n_points=200)
    assert abs(r.trace("th.out")[-1]) < 1e-3          # held upright
    m = by_file["cruise_control.evx"]
    r = simulate(m, t_end=40.0, n_points=200)
    # The PI is still closing the last 1 % at 40 s.
    assert r.trace("G.out")[-1] == pytest.approx(10.0, rel=0.01)


# ──────────────────────────────────────────────────────────────
#  The Model tab and the console
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def tab(app):
    from evans.console import Interpreter
    from evans.ui.sim.sim_tab import SimTab
    it = Interpreter()
    widget = SimTab()
    widget.set_evaluator(it.evaluate)
    shown = []
    it.simulink = widget.bridge(shown.append)
    widget.simulated.connect(lambda r: it.namespace.__setitem__("result", r))
    yield widget, it, shown
    widget.shutdown()
    widget.deleteLater()


def _run(app, widget):
    import time
    widget.run_simulation()
    deadline = time.monotonic() + 30
    while widget._thread is not None and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    app.processEvents()


def test_a_canvas_run_reads_the_workspace(app, tab):
    widget, it, _ = tab
    it.command("Kp = 9;")
    model = loop()
    model.block("K").set_param("gain", "Kp")
    widget._canvas.set_model(model)
    widget._t_end.setValue(3.0)
    _run(app, widget)
    # 9/(s+10) closed loop: 0.9 at steady state.
    assert it.namespace["result"].trace("G.out")[-1] == pytest.approx(
        0.9, rel=1e-4)


def test_the_toolbar_and_get_param_share_the_stop_time(app, tab):
    widget, it, _ = tab
    widget._canvas.set_model(loop())
    widget._t_end.setValue(4.0)
    it.run_script("t = get_param('loop', 'StopTime');", "matlab")
    assert it.namespace["t"] == "4"
    it.run_script("set_param('loop', 'StopTime', '7');", "matlab")
    assert widget._t_end.value() == 7.0


def test_set_param_at_the_console_redraws_the_canvas(app, tab):
    widget, it, _ = tab
    widget._canvas.set_model(loop())
    it.run_script("set_param('loop/K', 'Gain', '12');", "matlab")
    assert widget._canvas._blocks["K"].block.params["gain"] == 12.0


def test_open_system_shows_the_model(app, tab, tmp_path):
    widget, it, shown = tab
    loop().save(tmp_path / "other.fmdl")
    results = it.run_script("open_system('other');", "matlab",
                            folder=str(tmp_path))
    assert not [r for r in results if r.error]
    assert [m.name for m in shown] == ["other"]


def test_numeric_parameters_accept_expressions_in_the_editor(app):
    from evans.sim.block import create
    from evans.ui.sim.params import ParamForm
    form = ParamForm(create("Gain", "g"))
    form._editors["gain"].setText("2*Kp")
    assert form.commit() == {"gain": "2*Kp"}
    form._editors["gain"].setText("3.5")
    assert form.commit() == {"gain": 3.5}
    form._editors["gain"].setText("")
    assert form.commit() is None
    form.deleteLater()


def test_the_editor_shows_code_as_code(app):
    from evans.sim.block import create
    from evans.ui.sim.params import ParamForm
    form = ParamForm(create("MATLABFunction", "f"))
    editor = form._editors["code"]
    assert "function y = fcn(u)" in editor.toPlainText()
    form.deleteLater()


def test_the_block_label_shows_the_expression(app):
    m = loop()
    m.block("K").set_param("gain", "Kp")
    item = BlockItem(m.block("K"), 0, 0)
    assert item.block.display_label() == "Kp"


# ──────────────────────────────────────────────────────────────
#  A wire's name is its legend entry
# ──────────────────────────────────────────────────────────────

def _legend_names(scope):
    return [item.name() for item in scope._plot.getPlotItem().listDataItems()]


def test_a_named_wire_is_that_name_in_the_scope(app):
    m = loop()
    m.signal_names["G.out"] = "speed"
    result = simulate(m, t_end=1.0, n_points=20)
    assert result.label("G.out") == "speed"
    assert result.label("K.out") == "K.out"
    scope = ScopeWidget()
    scope.show_result(result, preferred=["G.out", "K.out"])
    assert sorted(_legend_names(scope)) == ["K.out", "speed"]
    assert scope._checks["G.out"].text() == "speed"
    scope.deleteLater()


def test_a_wire_name_survives_grouping_into_a_subsystem(app):
    m = loop()
    m.signal_names["G.out"] = "speed"      # inside the group: K and G
    m.signal_names["e.out"] = "error"      # outside it
    sub = group_into_subsystem(m, ["K", "G"], "plant")
    result = simulate(m, t_end=1.0, n_points=20)
    assert result.label("plant/G.out") == "speed"
    assert result.label("e.out") == "error"
    assert sub in {b.block_id for b in m}


# ──────────────────────────────────────────────────────────────
#  Clicking a wire, then deleting it
# ──────────────────────────────────────────────────────────────

def test_clicking_a_wire_and_deleting_it_does_not_crash(canvas, app):
    """
    A click on a wire's movable run began a bend drag, and releasing it
    without moving did ``float(None)`` inside a Qt override, which aborted
    the application.
    """
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    canvas.resize(900, 500)
    canvas.show()
    canvas.setFocus()
    app.processEvents()
    def wires():
        return sorted((i for i in canvas.scene().items()
                       if isinstance(i, WireItem)), key=lambda w: str(w.connection))

    assert len(wires()) == 4
    for k in range(4):
        wire = wires()[k]
        point = canvas.mapFromScene(
            wire.mapToScene(wire._path.pointAtPercent(0.5)))
        QTest.mouseClick(canvas.viewport(), Qt.LeftButton,
                         Qt.NoModifier, point)
        assert wires()[k].isSelected()
        QTest.keyClick(canvas, Qt.Key_Delete)
        assert len(canvas.model.connections) == 3
        canvas.undo_stack.undo()
        assert len(canvas.model.connections) == 4
        # The click was not a drag, so it must not have set a bend.
        assert not canvas.model.bends
