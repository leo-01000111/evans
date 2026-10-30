"""
Simulink and the workspace: parameters as expressions, To and From Workspace,
and the Simulink commands at the console.

Every expected value is worked out by hand or from a closed form: a gain of
``Kp`` on a step into ``1/(s+1)`` settles at ``Kp·(1 − e^{−t})``, a ramp
integrated is ``t²/2``. None is read back from an earlier Evans run.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from evans.console import Interpreter, matlab_runtime, set_figure_sink  # noqa: F401
from evans.console.figures import recording_sink
from evans.console.lib_sim import simulation_output  # after matlab_runtime
from evans.sim import CompileError, SimModel, simulate
from evans.sim.workspace import resolve_model


@pytest.fixture
def it():
    previous = set_figure_sink(recording_sink())
    yield Interpreter()
    set_figure_sink(previous)


def run(it, source: str, folder=None) -> str:
    results = it.run_script(source, "matlab",
                            folder=None if folder is None else str(folder))
    failed = [r for r in results if r.error]
    assert not failed, f"{failed[0].source!r} → {failed[0].error}"
    return "\n".join(r.output for r in results)


def error_of(it, source: str, folder=None) -> str:
    results = it.run_script(source, "matlab",
                            folder=None if folder is None else str(folder))
    failed = [r for r in results if r.error]
    assert failed, f"{source!r} ran without an error"
    return str(failed[0].error)


def first_order(gain="Kp", den="1, 1") -> SimModel:
    """A step through a gain into 1/(s+1)."""
    m = SimModel("first")
    m.add("Step", "r", step_time=0.0)
    m.add("Gain", "K", gain=gain)
    m.add("TransferFcn", "G", num="1", den=den)
    m.connect("r", "K")
    m.connect("K", "G")
    return m


# ──────────────────────────────────────────────────────────────
#  Parameters as workspace expressions
# ──────────────────────────────────────────────────────────────

def test_a_gain_named_after_a_variable_takes_the_workspace_value(it):
    it.command("Kp = 3;")
    result = simulate(first_order(), t_end=5.0, n_points=200,
                      evaluate=it.evaluate)
    assert result.trace("G.out")[-1] == pytest.approx(
        3 * (1 - math.exp(-5)), rel=1e-5)


def test_changing_the_variable_changes_the_next_run(it):
    model = first_order()
    finals = []
    for kp in (1, 2, 4):
        it.command(f"Kp = {kp};")
        finals.append(simulate(model, t_end=4.0, n_points=100,
                               evaluate=it.evaluate).trace("G.out")[-1])
    expected = [k * (1 - math.exp(-4)) for k in (1, 2, 4)]
    assert finals == pytest.approx(expected, rel=1e-5)


def test_expressions_vectors_and_matrices_are_evaluated(it):
    it.command("f = 0.5; den = [1 3 2]; A = [0 1; -2 -3];")
    m = SimModel("mixed")
    m.add("Sine", "s", amplitude="2", frequency="2*pi*f")
    m.add("Constant", "c", value="[1 2 3]")
    m.add("TransferFcn", "G", num="2", den="den")
    m.add("StateSpace", "P", A="A", B="[0; 1]", C="[1 0]", D="0")
    m.add("Step", "r", step_time=0.0)
    m.connect("r", "G")
    m.connect("s", "P")
    m.add("Terminator", "t")
    m.connect("c", "t")
    resolved = resolve_model(m, it.evaluate)
    assert resolved.block("s").params["frequency"] == pytest.approx(math.pi)
    assert list(resolved.block("c").params["value"]) == [1.0, 2.0, 3.0]
    assert resolved.block("P").params["A"].shape == (2, 2)
    # 2/((s+1)(s+2)) has DC gain 1.
    result = simulate(m, t_end=12.0, n_points=200, evaluate=it.evaluate)
    assert result.trace("G.out")[-1] == pytest.approx(1.0, abs=1e-4)
    assert result.signal("c.out")[-1].tolist() == [1.0, 2.0, 3.0]


def test_a_constant_expression_needs_no_workspace():
    m = SimModel("const")
    m.add("Constant", "c", value="2*pi")
    m.add("Terminator", "t")
    m.connect("c", "t")
    result = simulate(m, t_end=1.0, n_points=10)
    assert result.trace("c.out")[-1] == pytest.approx(2 * math.pi)


def test_an_undefined_variable_names_the_block_and_the_parameter():
    with pytest.raises(CompileError) as caught:
        simulate(first_order(), t_end=1.0)
    message = str(caught.value)
    assert "Gain 'K'" in message
    assert "Kp" in message
    assert "Unrecognized function or variable 'Kp'" in message


def test_a_value_the_block_rejects_names_the_block(it):
    it.command("umax = -1;")
    m = SimModel("sat")
    m.add("Constant", "c", value=0.0)
    m.add("Saturation", "S", upper="umax", lower=0.0)
    m.connect("c", "S")
    # Built without complaint: the stand-in is only a placeholder.
    assert m.block("S").expressions == {"upper": "umax"}
    with pytest.raises(CompileError, match="Saturation 'S'.*upper limit"):
        simulate(m, t_end=1.0, evaluate=it.evaluate)


def test_a_non_numeric_value_is_refused(it):
    it.command("name = 'abc';")
    with pytest.raises(CompileError, match="Gain 'K'"):
        simulate(first_order(gain="name"), t_end=1.0, evaluate=it.evaluate)


def test_the_saved_model_keeps_the_text(tmp_path, it):
    model = first_order(den="den")
    path = tmp_path / "first.fmdl"
    model.save(path)
    data = path.read_text(encoding="utf-8")
    assert '"gain": "Kp"' in data and '"den": "den"' in data
    restored = SimModel.load(path)
    assert restored.block("K").expressions == {"gain": "Kp"}
    it.command("Kp = 2; den = [2 1];")
    # 2/(2s+1) from a step: 2(1 − e^{−t/2}).
    result = simulate(restored, t_end=3.0, n_points=50, evaluate=it.evaluate)
    assert result.trace("G.out")[-1] == pytest.approx(
        2 * (1 - math.exp(-1.5)), rel=1e-5)


def test_numbers_typed_as_text_are_numbers():
    block = first_order(gain="2.5").block("K")
    assert block.params["gain"] == 2.5 and not block.expressions
    tf = first_order(den="1, 2").block("G")
    assert not tf.expressions


def test_an_expression_inside_a_subsystem_is_evaluated(it):
    inner = SimModel("inner")
    inner.add("Inport", "u", port_name="u", order=1)
    inner.add("Gain", "k", gain="Kc")
    inner.add("Outport", "y", port_name="y", order=1)
    inner.connect("u", "k")
    inner.connect("k", "y")
    m = SimModel("outer")
    m.add("Constant", "c", value=2.0)
    sub = m.add("Subsystem", "S", name="S")
    sub.set_inner(inner)
    m.add("Terminator", "t")
    m.connect("c", "S.u")
    m.connect("S.y", "t")
    it.command("Kc = 7;")
    result = simulate(m, t_end=1.0, n_points=10, evaluate=it.evaluate)
    assert result.trace("S/k.out")[-1] == pytest.approx(14.0)


def test_evaluating_leaves_the_workspace_alone(it):
    it.command("x = 4;")
    assert it.evaluate("x^2 + 1") == pytest.approx(17.0)
    assert "ans" not in it.namespace
    with pytest.raises(Exception, match="not a MATLAB expression"):
        it.evaluate("y = 3")
    assert "y" not in it.namespace


def test_the_label_shows_the_expression_not_the_stand_in():
    assert first_order().block("K").display_label() == "Kp"
    tf = first_order(den="den").block("G")
    assert "den" in tf.display_label()


# ──────────────────────────────────────────────────────────────
#  From Workspace and To Workspace
# ──────────────────────────────────────────────────────────────

def ramp_into_integrator(data: str) -> SimModel:
    m = SimModel("ramp")
    m.add("FromWorkspace", "u", data=data)
    m.add("Integrator", "I")
    m.connect("u", "I")
    return m


@pytest.mark.parametrize("setup", [
    "simin = [0 0; 10 10];",
    "simin.time = [0; 10]; simin.signals.values = [0; 10];",
    "simin.Time = [0; 10]; simin.Data = [0; 10];",
])
def test_from_workspace_reads_each_form(it, setup):
    it.command(setup)
    result = simulate(ramp_into_integrator("simin"), t_end=4.0, n_points=100,
                      evaluate=it.evaluate)
    # u = t, so its integral is t²/2.
    assert result.trace("u.out")[-1] == pytest.approx(4.0, rel=1e-9)
    assert result.trace("I.out")[-1] == pytest.approx(8.0, rel=1e-5)


def test_from_workspace_after_the_last_sample(it):
    it.command("d = [0 0; 1 2];")
    for after, expected in (("Extrapolation", 6.0), ("Setting to zero", 0.0),
                            ("Holding final value", 2.0)):
        m = ramp_into_integrator("d")
        m.block("u").set_param("after", after)
        result = simulate(m, t_end=3.0, n_points=31, evaluate=it.evaluate)
        assert result.trace("u.out")[-1] == pytest.approx(expected), after


def test_from_workspace_without_interpolation_holds_each_sample(it):
    it.command("d = [0 1; 1 5; 2 9];")
    m = ramp_into_integrator("d")
    m.block("u").set_param("interpolate", False)
    result = simulate(m, t_end=1.5, n_points=16, evaluate=it.evaluate)
    t, u = result.t, result.trace("u.out")
    assert u[np.searchsorted(t, 0.5)] == 1.0
    assert u[-1] == 5.0


def test_from_workspace_with_two_signals_is_two_wide(it):
    it.command("d = [0 1 2; 10 1 2];")
    m = SimModel("wide")
    m.add("FromWorkspace", "u", data="d")
    m.add("Terminator", "t")
    m.connect("u", "t")
    result = simulate(m, t_end=1.0, n_points=5, evaluate=it.evaluate)
    assert result.signal("u.out").shape[1] == 2


def test_from_workspace_refuses_a_one_column_matrix(it):
    it.command("d = [1; 2; 3];")
    with pytest.raises(CompileError, match="two columns"):
        simulate(ramp_into_integrator("d"), t_end=1.0, evaluate=it.evaluate)


def test_to_workspace_formats():
    m = first_order(gain=2.0)
    for name, fmt in (("a", "Array"), ("s", "Structure With Time"),
                      ("ts", "Timeseries")):
        m.add("ToWorkspace", name, name=name, format=fmt)
        m.connect("G", name)
    out = simulation_output(simulate(m, t_end=2.0, n_points=40))
    expected = 2 * (1 - math.exp(-2))
    assert out.tout.shape == (len(out.a), 1)
    assert out.a[-1, 0] == pytest.approx(expected, rel=1e-5)
    assert out.s.signals["values"][-1, 0] == pytest.approx(expected, rel=1e-5)
    assert out.s.time[-1, 0] == pytest.approx(2.0)
    assert out.ts.Data[-1, 0] == pytest.approx(expected, rel=1e-5)
    assert out.ts.Time[-1, 0] == pytest.approx(2.0)


# ──────────────────────────────────────────────────────────────
#  The Simulink commands at the console
# ──────────────────────────────────────────────────────────────

BUILD = """
new_system('loop');
add_block('simulink/Sources/Step', 'loop/r', 'StepTime', '0');
add_block('simulink/Math Operations/Gain', 'loop/K', 'Gain', 'Kp');
add_block('simulink/Continuous/Transfer Fcn', 'loop/G', 'Denominator', '[1 1]');
add_block('simulink/Sinks/To Workspace', 'loop/y', 'VariableName', 'y', ...
          'SaveFormat', 'Array');
add_block('simulink/Sinks/Out1', 'loop/out');
add_line('loop', 'r/1', 'K/1');
add_line('loop', 'K/1', 'G/1');
add_line('loop', 'G/1', 'y/1');
add_line('loop', 'G/1', 'out/1');
set_param('loop', 'StopTime', '6');
"""


def test_a_model_built_at_the_console_runs(it):
    run(it, BUILD + "Kp = 2; out = sim('loop');")
    out = it.namespace["out"]
    expected = 2 * (1 - math.exp(-6))
    assert out.tout[-1, 0] == pytest.approx(6.0)
    assert out.y[-1, 0] == pytest.approx(expected, rel=1e-5)
    assert out.yout.shape == (len(out.tout), 1)
    assert out.yout[-1, 0] == pytest.approx(expected, rel=1e-5)


def test_a_parameter_sweep_in_a_loop(it):
    run(it, BUILD + """
finals = zeros(1, 3);
for k = 1:3
    Kp = k;
    o = sim('loop');
    finals(k) = o.y(end);
end
""")
    expected = [k * (1 - math.exp(-6)) for k in (1, 2, 3)]
    assert it.namespace["finals"].reshape(-1).tolist() == pytest.approx(
        expected, rel=1e-5)


def test_get_param_and_set_param(it):
    run(it, BUILD + """
g = get_param('loop/K', 'Gain');
t = get_param('loop', 'StopTime');
set_param('loop/K', 'Gain', '5');
g2 = get_param('loop/K', 'Gain');
bt = get_param('loop/G', 'BlockType');
set_param('loop/G', 'Numerator', '[2]');
n = get_param('loop/G', 'num');
""")
    ns = it.namespace
    assert ns["g"] == "Kp"
    assert ns["t"] == "6"
    assert ns["g2"] == "5"
    assert ns["bt"] == "TransferFcn"
    assert ns["n"] == "[2]"


def test_sim_options_override_the_model(it):
    run(it, BUILD + "Kp = 1; o = sim('loop', 'StopTime', '2', "
                    "'Solver', 'ode15s');")
    assert it.namespace["o"].tout[-1, 0] == pytest.approx(2.0)
    run(it, "o2 = sim('loop', 3);")
    assert it.namespace["o2"].tout[-1, 0] == pytest.approx(3.0)


def test_save_and_load_by_name(it, tmp_path):
    run(it, BUILD + "save_system('loop'); close_system('loop');",
        folder=tmp_path)
    assert (tmp_path / "loop.fmdl").exists()
    run(it, "Kp = 1; o = sim('loop'); names = find_system('loop', "
            "'BlockType', 'Gain');", folder=tmp_path)
    assert it.namespace["o"].y[-1, 0] == pytest.approx(1 - math.exp(-6),
                                                       rel=1e-5)
    assert list(it.namespace["names"]) == ["loop/K"]


def test_delete_block_and_line(it):
    run(it, BUILD + """
delete_line('loop', 'G/1', 'y/1');
delete_block('loop/y');
""")
    model = it._matlab_runtime().models["loop"]
    assert "y" not in model.blocks
    assert all(c.dst.block != "y" for c in model.connections)


def test_console_errors_name_the_problem(it):
    run(it, BUILD)
    assert "no parameter 'Frobnicate'" in error_of(
        it, "get_param('loop/K', 'Frobnicate')")
    assert "'nowhere' is not loaded" in error_of(it, "sim('nowhere')")
    assert "no block 'Frob'" in error_of(it, "add_block('Frob', 'loop/f')")
    assert "Kp" in error_of(it, "clear Kp; sim('loop')")


def test_set_param_inside_a_subsystem(it):
    run(it, """
new_system('m');
add_block('Constant', 'm/c', 'Value', '2');
add_block('Subsystem', 'm/S');
add_block('Inport', 'm/S/u');
add_block('Gain', 'm/S/k', 'Gain', '3');
add_block('Outport', 'm/S/y');
add_line('m/S', 'u/1', 'k/1');
add_line('m/S', 'k/1', 'y/1');
add_block('Out1', 'm/out');
add_line('m', 'c/1', 'S/1');
add_line('m', 'S/1', 'out/1');
set_param('m/S/k', 'Gain', '10');
o = sim('m', 1);
""")
    assert it.namespace["o"].yout[-1, 0] == pytest.approx(20.0)


def test_a_model_object_still_returns_the_python_result(it):
    it.namespace["mdl"] = first_order(gain=1.0)
    run(it, "r = sim(mdl, 2);")
    assert len(it.namespace["r"].t) > 10
