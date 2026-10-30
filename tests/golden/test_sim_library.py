"""
The blocks added for daily Simulink use: MATLAB code blocks, logic, the
missing common blocks, Goto/From and data stores, conditionally executed
subsystems and the Integrator's reset port.

Expected values come from the definition of each block or a closed form
(an integral of a constant is a ramp, a counter counts), never from an
earlier Evans run.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from evans.console import Interpreter
from evans.sim import CompileError, SimModel, simulate


def at(result, name: str, t: float) -> float:
    """A signal's value at the last logged instant not after ``t``."""
    k = int(np.searchsorted(result.t, t, side="right")) - 1
    return float(result.trace(name)[max(k, 0)])


def sink(m: SimModel, src: str, name: str = "t") -> None:
    m.add("Terminator", name)
    m.connect(src, name)


# ──────────────────────────────────────────────────────────────
#  Fcn and MATLAB Function
# ──────────────────────────────────────────────────────────────

def test_fcn_applies_a_matlab_expression_to_a_vector():
    m = SimModel("fcn")
    m.add("Clock", "c")
    m.add("Sine", "s")
    m.add("Mux", "mx", n_inputs=2)
    m.add("Fcn", "f", expr="u(1)^2 + 3*u(2)")
    m.connect("c", "mx.in1")
    m.connect("s", "mx.in2")
    m.connect("mx", "f")
    sink(m, "f")
    r = simulate(m, t_end=2.0, n_points=21)
    assert np.allclose(r.trace("f.out"), r.t ** 2 + 3 * np.sin(r.t))


def test_fcn_reads_a_workspace_variable_when_the_model_runs():
    it = Interpreter()
    it.command("k = 5;")
    m = SimModel("fcn")
    m.add("Constant", "c", value=2.0)
    m.add("Fcn", "f", expr="k*u")
    m.connect("c", "f")
    sink(m, "f")
    assert simulate(m, t_end=1.0, n_points=5,
                    evaluate=it.evaluate).trace("f.out")[-1] == 10.0


def test_matlab_function_ports_follow_its_signature():
    m = SimModel("mfb")
    block = m.add("MATLABFunction", "g", code=(
        "function [s, d] = fcn(a, b)\n"
        "s = a + b;\n"
        "d = a - b;\n"))
    assert block.inputs == ["a", "b"] and block.outputs == ["s", "d"]
    m.add("Constant", "x", value=5.0)
    m.add("Constant", "y", value=2.0)
    m.connect("x", "g.a")
    m.connect("y", "g.b")
    sink(m, "g.s", "t1")
    sink(m, "g.d", "t2")
    r = simulate(m, t_end=1.0, n_points=5)
    assert r.trace("g.s")[-1] == 7.0 and r.trace("g.d")[-1] == 3.0


def test_a_matlab_function_integrated_matches_the_closed_form():
    # y' = −y·u with u = 1: y = e^{−t}.
    m = SimModel("ode")
    m.add("Constant", "u", value=1.0)
    m.add("Integrator", "y", x0=1.0)
    m.add("MATLABFunction", "f", code=(
        "function dy = rhs(y, u)\ndy = -y*u;\n"))
    m.connect("y", "f.y")
    m.connect("u", "f.u")
    m.connect("f", "y")
    r = simulate(m, t_end=2.0, n_points=21)
    assert r.trace("y.out")[-1] == pytest.approx(math.exp(-2), rel=1e-5)


def test_code_that_does_not_parse_is_refused_when_edited():
    from evans.sim.block import BlockError, create
    with pytest.raises(BlockError, match="does not parse"):
        create("Fcn", "f", expr="u(1 +")
    with pytest.raises(BlockError, match="function line"):
        create("MATLABFunction", "g", code="y = u;")


def test_a_runtime_error_names_the_block_and_the_time():
    m = SimModel("bad")
    m.add("Constant", "c", value=1.0)
    m.add("Fcn", "f", expr="u(3)")
    m.connect("c", "f")
    sink(m, "f")
    with pytest.raises(Exception, match="Fcn 'f' failed at t ="):
        simulate(m, t_end=1.0)


# ──────────────────────────────────────────────────────────────
#  Logic
# ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("op, expected", [
    ("<", [1, 0, 0]), ("<=", [1, 1, 0]), (">", [0, 0, 1]),
    (">=", [0, 1, 1]), ("==", [0, 1, 0]), ("~=", [1, 0, 1]),
])
def test_relational_operator(op, expected):
    m = SimModel("rel")
    m.add("Constant", "a", value=[1.0, 2.0, 3.0])
    m.add("Constant", "b", value=2.0)
    m.add("RelationalOperator", "r", operator=op)
    m.connect("a", "r.in1")
    m.connect("b", "r.in2")
    sink(m, "r")
    out = simulate(m, t_end=1.0, n_points=3).signal("r.out")[-1]
    assert out.tolist() == expected


def test_compare_to_constant_switches_on_the_exact_instant():
    # A ramp crosses 1.5 at t = 1.5; the zero crossing must land there.
    m = SimModel("cmp")
    m.add("Clock", "c")
    m.add("CompareToConstant", "k", operator=">=", constant=1.5)
    m.add("Integrator", "I")
    m.connect("c", "k")
    m.connect("k", "I")
    r = simulate(m, t_end=3.0, n_points=7)
    # ∫ of the step: t − 1.5 after the crossing.
    assert r.trace("I.out")[-1] == pytest.approx(1.5, abs=1e-6)


def test_compare_to_zero():
    m = SimModel("z")
    m.add("Constant", "c", value=[-1.0, 0.0, 1.0])
    m.add("CompareToZero", "k", operator=">")
    m.connect("c", "k")
    sink(m, "k")
    assert simulate(m, t_end=1.0).signal("k.out")[-1].tolist() == [0, 0, 1]


@pytest.mark.parametrize("op, expected", [
    ("AND", [0, 0, 0, 1]), ("OR", [0, 1, 1, 1]), ("NAND", [1, 1, 1, 0]),
    ("NOR", [1, 0, 0, 0]), ("XOR", [0, 1, 1, 0]),
])
def test_logical_operator_truth_tables(op, expected):
    m = SimModel("logic")
    m.add("Constant", "a", value=[0.0, 0.0, 2.0, -3.0])
    m.add("Constant", "b", value=[0.0, 1.0, 0.0, 0.5])
    m.add("LogicalOperator", "L", operator=op)
    m.connect("a", "L.in1")
    m.connect("b", "L.in2")
    sink(m, "L")
    assert simulate(m, t_end=1.0).signal("L.out")[-1].tolist() == expected


def test_logical_not_has_one_input():
    from evans.sim.block import create
    assert create("LogicalOperator", "n", operator="NOT").inputs == ["in1"]


@pytest.mark.parametrize("op, mask, expected", [
    ("AND", 0b1100, 0b1000), ("OR", 0b0011, 0b1011), ("XOR", 0b1111, 0b0101),
])
def test_bitwise_operator_with_a_mask(op, mask, expected):
    m = SimModel("bits")
    m.add("Constant", "a", value=float(0b1010))
    m.add("BitwiseOperator", "B", operator=op, mask=float(mask))
    m.connect("a", "B")
    sink(m, "B")
    assert simulate(m, t_end=1.0).trace("B.out")[-1] == expected


def test_bitwise_not_is_32_bit():
    m = SimModel("not")
    m.add("Constant", "a", value=0.0)
    m.add("BitwiseOperator", "B", operator="NOT")
    m.connect("a", "B")
    sink(m, "B")
    assert simulate(m, t_end=1.0).trace("B.out")[-1] == 2.0 ** 32 - 1


# ──────────────────────────────────────────────────────────────
#  Common blocks
# ──────────────────────────────────────────────────────────────

def discrete_chain(block_type: str, **params) -> SimModel:
    """A ramp sampled every second into the block under test."""
    m = SimModel("chain")
    m.add("Clock", "c")
    m.add("ZeroOrderHold", "h", sample_time=1.0)
    m.add(block_type, "b", sample_time=1.0, **params)
    m.connect("c", "h")
    m.connect("h", "b")
    sink(m, "b")
    return m


def test_memory_is_one_sample_behind_its_input():
    # Sampling the time itself: at hit k Memory shows the sample k − 1.
    m = SimModel("mem")
    m.add("Clock", "c")
    m.add("Memory", "b", sample_time=1.0, x0=-1.0)
    m.connect("c", "b")
    sink(m, "b")
    r = simulate(m, t_end=5.0, n_points=11)
    assert [at(r, "b.out", k + 0.5) for k in range(5)] == [-1, 0, 1, 2, 3]


@pytest.mark.parametrize("method, gain_at_4", [
    # Σ over the samples the integrator has seen, by its rule; the hold
    # gives it 0, 0, 1, 2, 3 at hits 0…4 (see the Memory test).
    ("Forward Euler", 0 + 0 + 1 + 2),
    ("Backward Euler", 0 + 0 + 1 + 2 + 3),
    ("Trapezoidal", (0 + 0) / 2 + (0 + 1) / 2 + (1 + 2) / 2 + (2 + 3) / 2),
])
def test_discrete_integrator_methods(method, gain_at_4):
    r = simulate(discrete_chain("DiscreteIntegrator", method=method),
                 t_end=4.0, n_points=9)
    assert r.trace("b.out")[-1] == pytest.approx(gain_at_4)


def test_discrete_integrator_limits():
    r = simulate(discrete_chain("DiscreteIntegrator", limit=True, upper=2.0,
                                lower=-1.0), t_end=8.0, n_points=17)
    assert r.trace("b.out").max() == 2.0


def test_discrete_fir_is_a_moving_sum():
    m = SimModel("fir")
    m.add("Clock", "c")
    m.add("DiscreteFIR", "b", coefficients="1, 1, 1", sample_time=1.0)
    m.connect("c", "b")
    sink(m, "b")
    r = simulate(m, t_end=6.0, n_points=13)
    # The sum of the last three samples of t: k + (k − 1) + (k − 2).
    assert [at(r, "b.out", k + 0.5) for k in range(6)] == [0, 1, 3, 6, 9, 12]


def test_discrete_filter_in_powers_of_z_inverse():
    # 1/(1 − 0.5 z⁻¹) on a unit step: 1, 1.5, 1.75, … → 2.
    m = SimModel("filt")
    m.add("Constant", "c", value=1.0)
    m.add("DiscreteFilter", "f", num="1", den="1, -0.5", sample_time=0.1)
    m.connect("c", "f")
    sink(m, "f")
    r = simulate(m, t_end=0.25, n_points=6)
    # y(0) = 1: the filter acts at t = 0, as every discrete block does.
    assert [at(r, "f.out", t) for t in (0.05, 0.15, 0.25)] == \
        pytest.approx([1.0, 1.5, 1.75])


def test_counter_wraps_after_its_upper_limit():
    m = SimModel("count")
    m.add("Counter", "n", upper=2, sample_time=1.0)
    sink(m, "n")
    r = simulate(m, t_end=5.0, n_points=11)
    assert [at(r, "n.out", k + 0.5) for k in range(6)] == [0, 1, 2, 0, 1, 2]


def test_repeating_sequence_is_a_sawtooth():
    m = SimModel("saw")
    m.add("RepeatingSequence", "s", times="0, 2", values="0, 4")
    sink(m, "s")
    r = simulate(m, t_end=5.0, n_points=51)
    assert at(r, "s.out", 1.0) == pytest.approx(2.0)
    assert at(r, "s.out", 3.0) == pytest.approx(2.0)
    assert at(r, "s.out", 4.5) == pytest.approx(1.0)


def test_signal_builder_steps_and_holds():
    m = SimModel("sb")
    m.add("SignalBuilder", "s", times="0, 1, 1, 2", values="0, 0, 3, 3")
    m.add("Integrator", "I")
    m.connect("s", "I")
    r = simulate(m, t_end=4.0, n_points=41)
    assert at(r, "s.out", 0.5) == 0.0 and at(r, "s.out", 3.5) == 3.0
    # ∫: 3·(t − 1), the step landed on exactly t = 1.
    assert r.trace("I.out")[-1] == pytest.approx(9.0, abs=1e-6)


def test_lookup_2d_is_bilinear_and_clamped():
    m = SimModel("lut")
    m.add("Constant", "a", value=[0.5, 5.0])
    m.add("Constant", "b", value=[0.5, -5.0])
    m.add("Lookup2D", "L", rows="0, 1", cols="0, 1", table="0 1; 2 3")
    m.connect("a", "L.u1")
    m.connect("b", "L.u2")
    sink(m, "L")
    out = simulate(m, t_end=1.0).signal("L.out")[-1]
    # z = 2·u1 + u2 on the square; (5, −5) clamps to (1, 0).
    assert out.tolist() == pytest.approx([1.5, 2.0])


def test_prelookup_and_interpolation():
    m = SimModel("pre")
    m.add("Constant", "u", value=1.25)
    m.add("Prelookup", "p", breakpoints="0, 1, 2")
    m.add("PrelookupInterp", "i", table="0, 10, 30")
    m.connect("u", "p")
    m.connect("p.k", "i.k")
    m.connect("p.f", "i.f")
    sink(m, "i")
    r = simulate(m, t_end=1.0)
    assert r.trace("p.k")[-1] == 1.0
    assert r.trace("p.f")[-1] == pytest.approx(0.25)
    assert r.trace("i.out")[-1] == pytest.approx(15.0)


def test_xy_graph_records_its_two_signals():
    m = SimModel("xy")
    m.add("Sine", "s")
    m.add("Clock", "c")
    m.add("XYGraph", "g", title="Lissajous")
    m.connect("c", "g.x")
    m.connect("s", "g.y")
    assert simulate(m, t_end=1.0).xy == {"Lissajous": ("c.out", "s.out")}


# ──────────────────────────────────────────────────────────────
#  Goto/From and data stores
# ──────────────────────────────────────────────────────────────

def test_goto_and_from_carry_a_signal_by_name():
    m = SimModel("goto")
    m.add("Clock", "c")
    m.add("Goto", "g", tag="T")
    m.add("From", "f", tag="T")
    m.add("Gain", "k", gain=2.0)
    m.connect("c", "g")
    m.connect("f", "k")
    sink(m, "k")
    assert simulate(m, t_end=3.0).trace("k.out")[-1] == pytest.approx(6.0)


def test_a_local_tag_does_not_reach_into_a_subsystem():
    inner = SimModel("in")
    inner.add("From", "f", tag="T")
    inner.add("Outport", "y", port_name="y")
    inner.connect("f", "y")
    m = SimModel("scoped")
    m.add("Clock", "c")
    m.add("Goto", "g", tag="T", visibility="local")
    m.connect("c", "g")
    sub = m.add("Subsystem", "S")
    sub.set_inner(inner)
    sink(m, "S.y")
    with pytest.raises(CompileError, match="no Goto"):
        simulate(m, t_end=1.0)
    m.block("g").set_param("visibility", "global")
    m.remove("t")
    m.add("Gain", "k", gain=1.0)
    m.connect("S.y", "k")
    assert simulate(m, t_end=2.0).trace("k.out")[-1] == pytest.approx(2.0)


def test_two_gotos_with_one_tag_are_refused():
    m = SimModel("dup")
    m.add("Clock", "c")
    m.add("Goto", "g1", tag="T")
    m.add("Goto", "g2", tag="T")
    m.connect("c", "g1")
    m.connect("c", "g2")
    with pytest.raises(CompileError, match="both send the tag 'T'"):
        simulate(m, t_end=1.0)


def test_data_store_read_gets_the_written_signal_or_the_initial_value():
    m = SimModel("ds")
    m.add("DataStoreMemory", "mem", store="A", initial=7.0)
    m.add("DataStoreRead", "r", store="A")
    sink(m, "r", "t1")
    assert simulate(m, t_end=1.0).trace("r.out")[-1] == 7.0
    m.add("Clock", "c")
    m.add("DataStoreWrite", "w", store="A")
    m.connect("c", "w")
    m.remove("t1")
    m.add("Gain", "k", gain=3.0)
    m.connect("r", "k")
    assert simulate(m, t_end=2.0).trace("k.out")[-1] == pytest.approx(6.0)


def test_an_undeclared_data_store_is_refused():
    m = SimModel("ds")
    m.add("DataStoreRead", "r", store="B")
    sink(m, "r")
    with pytest.raises(CompileError, match="no Data Store Memory"):
        simulate(m, t_end=1.0)


# ──────────────────────────────────────────────────────────────
#  Conditionally executed subsystems
# ──────────────────────────────────────────────────────────────

def enabled_integrator(states="held", when="held") -> SimModel:
    """∫1 inside a subsystem enabled on [0, 2), [4, 6) … by a pulse."""
    inner = SimModel("in")
    inner.add("Enable", "en", states=states)
    inner.add("Inport", "u", port_name="u", order=1)
    inner.add("Integrator", "I")
    inner.add("Outport", "y", port_name="y", order=1, when_disabled=when,
              initial=-1.0)
    inner.connect("u", "I")
    inner.connect("I", "y")
    m = SimModel("top")
    m.add("Constant", "one", value=1.0)
    m.add("Pulse", "p", amplitude=1.0, period=4.0, duty=0.5)
    sub = m.add("Subsystem", "S")
    sub.set_inner(inner)
    m.add("Gain", "out", gain=1.0)
    m.connect("one", "S.u")
    m.connect("p", "S.enable")
    m.connect("S.y", "out")
    return m


def test_an_enabled_subsystem_gains_an_enable_port():
    assert enabled_integrator().block("S").inputs == ["u", "enable"]


@pytest.mark.parametrize("states, when, expected", [
    # Enabled on [0, 2) and [4, 6): the state freezes at 2 while disabled.
    ("held", "held", [1.0, 2.0, 3.0, 2.0 + 1.0]),
    # Reset states: the integral starts again from 0 at t = 4.
    ("reset", "held", [1.0, 2.0, 1.0, 1.0]),
    # Reset output: the initial output, −1, while disabled.
    ("held", "reset", [1.0, -1.0, 3.0, 3.0]),
])
def test_enabled_subsystem(states, when, expected):
    r = simulate(enabled_integrator(states, when), t_end=7.0, n_points=71)
    got = [at(r, "out.out", t) for t in (1.0, 3.0, 5.0)]
    assert got == pytest.approx(expected[:3], abs=1e-6)


def test_a_disabled_subsystems_state_does_not_move():
    r = simulate(enabled_integrator(), t_end=4.0, n_points=41)
    assert at(r, "S/I.out", 2.5) == pytest.approx(2.0, abs=1e-6)
    assert at(r, "S/I.out", 3.9) == pytest.approx(2.0, abs=1e-6)


def triggered_counter(edge="rising") -> SimModel:
    inner = SimModel("cnt")
    inner.add("Trigger", "tr", edge=edge)
    inner.add("Counter", "n", upper=100, sample_time=1.0)
    inner.add("Outport", "y", port_name="y")
    inner.connect("n", "y")
    m = SimModel("trig")
    # High on [0, 0.5), [1, 1.5) …: rising edges at 1, 2, 3, 4; falling at
    # 0.5, 1.5, 2.5, …
    m.add("Pulse", "p", amplitude=1.0, period=1.0, duty=0.5)
    sub = m.add("Subsystem", "T")
    sub.set_inner(inner)
    m.add("Gain", "out", gain=1.0)
    m.connect("p", "T.trigger")
    m.connect("T.y", "out")
    return m


@pytest.mark.parametrize("edge, edges_by_3_7", [
    ("rising", 3), ("falling", 4), ("either", 7),
])
def test_a_triggered_subsystem_runs_once_per_edge(edge, edges_by_3_7):
    # A Counter counts its updates: after n edges it holds n (post-update
    # output, as at a sample hit, starting from the count before: n − 1 + 1).
    r = simulate(triggered_counter(edge), t_end=3.7, n_points=38)
    assert at(r, "out.out", 3.7) == pytest.approx(edges_by_3_7 - 1)


def test_a_triggered_subsystem_refuses_continuous_states():
    inner = SimModel("in")
    inner.add("Trigger", "tr")
    inner.add("Integrator", "I")
    m = SimModel("top")
    m.add("Pulse", "p")
    sub = m.add("Subsystem", "T")
    sub.set_inner(inner)
    m.connect("p", "T.trigger")
    with pytest.raises(CompileError, match="cannot hold continuous states"):
        simulate(m, t_end=1.0)


def action(value: float) -> SimModel:
    inner = SimModel("act")
    inner.add("ActionPort", "ap")
    inner.add("Constant", "c", value=value)
    inner.add("Outport", "y", port_name="y", when_disabled="reset")
    inner.connect("c", "y")
    return inner


def test_if_drives_one_action_subsystem_at_a_time():
    m = SimModel("if")
    m.add("Sine", "s")
    m.add("If", "branch", if_expr="u1 > 0.5", elseif_exprs="u1 < -0.5")
    for name, value, port in (("A", 1.0, "if"), ("B", -1.0, "elseif1"),
                              ("C", 10.0, "else")):
        sub = m.add("Subsystem", name)
        sub.set_inner(action(value))
        m.connect(f"branch.{port}", f"{name}.action")
    m.add("Sum", "total", signs="+++")
    m.connect("A.y", "total.in1")
    m.connect("B.y", "total.in2")
    m.connect("C.y", "total.in3")
    m.connect("s", "branch.u1")
    r = simulate(m, t_end=6.0, n_points=61)
    for t, expected in ((math.pi / 2, 1.0), (3 * math.pi / 2, -1.0),
                        (math.pi, 10.0)):
        assert at(r, "total.out", t) == expected, t


def test_switch_case_picks_a_case_or_the_default():
    m = SimModel("sw")
    m.add("Constant", "c", value=2.7)
    m.add("SwitchCase", "s", cases="1, [2 3]")
    m.connect("c", "s")
    for port in ("case1", "case2", "default"):
        sink(m, f"s.{port}", f"t_{port}")
    r = simulate(m, t_end=1.0)
    assert [r.trace(f"s.{p}")[-1] for p in ("case1", "case2", "default")] \
        == [0.0, 1.0, 0.0]


def test_a_subsystem_takes_one_control_port():
    inner = SimModel("in")
    inner.add("Enable", "en")
    inner.add("Trigger", "tr")
    m = SimModel("top")
    sub = m.add("Subsystem", "S")
    with pytest.raises(Exception, match="one control port"):
        sub.set_inner(inner)


# ──────────────────────────────────────────────────────────────
#  Integrator reset
# ──────────────────────────────────────────────────────────────

def reset_integrator(kind: str) -> SimModel:
    m = SimModel("rst")
    m.add("Constant", "one", value=1.0)
    # High on [3, 3.3), [6, 6.3), …
    m.add("Pulse", "p", amplitude=1.0, period=3.0, duty=0.1, delay=3.0)
    m.add("Integrator", "I", x0=0.5, reset=kind)
    m.connect("one", "I.in")
    m.connect("p", "I.reset")
    return m


@pytest.mark.parametrize("kind, at_5, at_8", [
    ("rising", 0.5 + 2.0, 0.5 + 2.0),       # reset at 3 and 6
    ("falling", 0.5 + 1.7, 0.5 + 1.7),      # reset at 3.3 and 6.3
    ("level", 0.5 + 1.7, 0.5 + 1.7),        # held at x0 while high
])
def test_integrator_reset(kind, at_5, at_8):
    r = simulate(reset_integrator(kind), t_end=8.0, n_points=81)
    assert at(r, "I.out", 5.0) == pytest.approx(at_5, abs=1e-6)
    assert at(r, "I.out", 8.0) == pytest.approx(at_8, abs=1e-6)


def test_integrator_reset_either_edge():
    r = simulate(reset_integrator("either"), t_end=5.0, n_points=51)
    # Reset at 3 and again at 3.3.
    assert at(r, "I.out", 5.0) == pytest.approx(0.5 + 1.7, abs=1e-6)


def test_integrator_reset_with_a_fixed_step_solver():
    r = simulate(reset_integrator("rising"), t_end=5.0, solver="ode4",
                 max_step=0.01, n_points=51)
    # Reset on the step that reaches t = 3.
    assert at(r, "I.out", 3.0) == pytest.approx(0.5, abs=1e-9)
    assert at(r, "I.out", 4.5) == pytest.approx(2.0, abs=1e-6)
