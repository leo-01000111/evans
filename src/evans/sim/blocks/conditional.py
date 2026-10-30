"""
Conditionally executed subsystems.
==================================
Put an ``Enable``, ``Trigger`` or ``ActionPort`` block inside a subsystem
and the subsystem gains a control input:

* **enabled** — the contents run while the enable signal is positive. While
  disabled, their states are frozen, and on re-enabling they are either kept
  (``held``) or put back to their initial values (``reset``).
* **triggered** — the contents run once at each rising, falling or either
  edge of the trigger signal, and their outputs are held between edges.
  Only discrete blocks may sit inside, as in Simulink.
* **action** — driven by an ``If`` or ``SwitchCase`` block, whose outputs
  are 1 for the branch taken and 0 for the rest; the subsystem runs while
  its action signal is 1, otherwise like an enabled one.

Each Outport inside says what the subsystem outputs while it is not running:
the last value (``held``) or its initial output (``reset``).

How it runs
-----------
:func:`evans.sim.compile.flatten` still splices the contents into the
parent. It adds a hidden **gate** block, wired to the control signal, and a
hidden **hold** block on each output, and tags every block inside with the
gate. The solver then asks each block whether its gates are open: a closed
gate freezes its members' continuous states and skips their discrete
updates. The gate watches its signal with a zero crossing, so the solver
stops on the exact instant it opens or closes, and the gate acts there
(:meth:`_Gate.fire`): resetting states, capturing held outputs, or running a
triggered subsystem's step.
"""

from __future__ import annotations

import re

import numpy as np

from ..block import Block, BlockError, ModeLatch, ParamSpec, register

_CAT = "Ports & Subsystems"
_HIDDEN = "Hidden"


# ──────────────────────────────────────────────────────────────
#  The control ports, placed inside a subsystem
# ──────────────────────────────────────────────────────────────

class _ControlPort(Block):
    """Marks its subsystem as conditional; never runs itself."""

    default_inputs = ()
    default_outputs = ()
    #: The subsystem input this block adds.
    port = ""

    def output_widths(self, input_widths):
        return []

    def output(self, t, x, xd, u):
        return []


@register
class Enable(_ControlPort):
    type_name = "Enable"
    category = _CAT
    description = "Inside a subsystem: run it only while the enable input is > 0."
    port = "enable"
    params_spec = (
        ParamSpec("states", "States when enabling", "held", kind="choice",
                  choices=("held", "reset")),
    )

    def label(self):
        return "enable"


@register
class Trigger(_ControlPort):
    type_name = "Trigger"
    category = _CAT
    description = "Inside a subsystem: run it once at each edge of the trigger."
    port = "trigger"
    params_spec = (
        ParamSpec("edge", "Trigger type", "rising", kind="choice",
                  choices=("rising", "falling", "either")),
    )

    def label(self):
        return f"trigger\n{self.params['edge']}"


@register
class ActionPort(_ControlPort):
    type_name = "ActionPort"
    category = _CAT
    description = "Inside a subsystem: run it when an If or Switch Case picks it."
    port = "action"
    params_spec = (
        ParamSpec("states", "States when execution resumes", "held",
                  kind="choice", choices=("held", "reset")),
    )

    def label(self):
        return "action"


CONTROL_PORTS = {"Enable": "enable", "Trigger": "trigger",
                 "ActionPort": "action"}


# ──────────────────────────────────────────────────────────────
#  If and Switch Case
# ──────────────────────────────────────────────────────────────

def _split_list(text: str) -> list[str]:
    """``'u1 < 0, u2 == 1'`` → its expressions, commas inside () kept."""
    parts, depth, current = [], 0, ""
    for ch in str(text):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        parts.append(current.strip())
    return parts


@register
class If(Block):
    """
    ``if`` / ``elseif`` / ``else`` on its inputs ``u1``, ``u2``, …: one output
    per branch, 1 for the branch taken and 0 for the others. Wire each to an
    action subsystem.
    """

    type_name = "If"
    category = _CAT
    description = "If / elseif / else on u1, u2, …; drives action subsystems."
    binds_workspace = True
    params_spec = (
        ParamSpec("n_inputs", "Number of inputs", 1, kind="int"),
        ParamSpec("if_expr", "If expression", "u1 > 0", kind="str"),
        ParamSpec("elseif_exprs", "Elseif expressions", "", kind="str",
                  help="Comma-separated, such as u1 < -1, u2 == 0."),
        ParamSpec("show_else", "Show else condition", True, kind="bool"),
    )

    def configure(self) -> None:
        from .user import _MatlabCode
        n = int(self.params["n_inputs"])
        if n < 1:
            raise BlockError("If needs at least one input")
        self.inputs = [f"u{i + 1}" for i in range(n)]
        exprs = [str(self.params["if_expr"]).strip(),
                 *_split_list(self.params["elseif_exprs"])]
        if not exprs[0]:
            raise BlockError("If needs an if expression")
        self._codes = [_MatlabCode(e, function=False) for e in exprs]
        self.outputs = ["if"] + [f"elseif{k}" for k in range(1, len(exprs))]
        if self.params["show_else"]:
            self.outputs.append("else")

    def bind(self, variables):
        for code in self._codes:
            code.bind(variables)

    def output_widths(self, input_widths):
        return [1] * len(self.outputs)

    def _branch(self, t, u) -> int:
        from .user import _matlab_value
        scope = {f"u{i + 1}": _matlab_value(v) for i, v in enumerate(u)}
        for k, code in enumerate(self._codes):
            try:
                value = code.run_scope(scope)
            except Exception as exc:                       # noqa: BLE001
                raise BlockError(
                    f"If {self.block_id!r} failed at t = {t:.6g}: "
                    f"{str(exc).strip() or type(exc).__name__}") from None
            if np.all(np.asarray(value) != 0) and np.size(value):
                return k
        return len(self._codes)             # else, or nothing

    def output(self, t, x, xd, u):
        taken = self._branch(t, u)
        return [np.array([1.0 if k == taken else 0.0])
                for k in range(len(self.outputs))]

    def label(self):
        return "if"


@register
class SwitchCase(Block):
    """
    ``switch`` on its input, truncated to a whole number: one output per
    case, 1 for the case that matches and 0 for the others, and a default.
    """

    type_name = "SwitchCase"
    category = _CAT
    description = "Switch on a whole number; drives action subsystems."
    params_spec = (
        ParamSpec("cases", "Case conditions", "1, 2", kind="str",
                  help="Comma-separated whole numbers; [3 4] is one case "
                       "matching either."),
        ParamSpec("show_default", "Show default case", True, kind="bool"),
    )

    def configure(self) -> None:
        self._cases: list[set[int]] = []
        for part in _split_list(self.params["cases"]):
            numbers = re.findall(r"[-+]?\d+", part)
            if not numbers:
                raise BlockError(f"Switch Case: {part!r} is not a case")
            self._cases.append({int(n) for n in numbers})
        if not self._cases:
            raise BlockError("Switch Case needs at least one case")
        self.outputs = [f"case{k + 1}" for k in range(len(self._cases))]
        if self.params["show_default"]:
            self.outputs.append("default")

    def output_widths(self, input_widths):
        return [1] * len(self.outputs)

    def output(self, t, x, xd, u):
        value = int(np.trunc(float(np.atleast_1d(u[0])[0]))) if u else 0
        taken = next((k for k, case in enumerate(self._cases)
                      if value in case), len(self._cases))
        return [np.array([1.0 if k == taken else 0.0])
                for k in range(len(self.outputs))]

    def label(self):
        return "switch\ncase"


# ──────────────────────────────────────────────────────────────
#  What the compiler adds: gates and holds
# ──────────────────────────────────────────────────────────────

class _Gate(ModeLatch, Block):
    """
    The control signal of one conditional subsystem.

    Its mode is the signal's side of zero, latched between crossings like
    any discontinuity's, so the solver stops where it changes. ``members``
    and ``holds`` are the block ids it governs, filled in by the compiler.
    """

    category = _HIDDEN
    hidden = True
    default_inputs = ("ctrl",)
    default_outputs = ()

    def configure(self) -> None:
        self.members: list[str] = []
        self.holds: list[str] = []
        self._acted: float | None = None

    def reset(self) -> None:
        super().reset()
        self._acted = None

    def output_widths(self, input_widths):
        return []

    def output(self, t, x, xd, u):
        return []

    @staticmethod
    def _signal(u) -> float:
        return float(np.atleast_1d(u[0])[0]) if u else 0.0

    def n_zero_crossings(self, input_widths):
        return 1

    def update_modes(self, t, x, xd, u):
        return self._latch(self._fresh_mode(u))

    def init_modes(self, t, x, xd, u):
        self._latch(self._fresh_mode(u))
        self._acted = float(self._mode[0])

    @property
    def running(self) -> bool:
        """Whether members run on their own: integrate, update on schedule."""
        return False

    def _ordered(self, ev, ids: list[str]) -> list:
        return sorted((ev.c.plans[b] for b in ids if b in ev.c.plans),
                      key=lambda p: p.order)


@register
class _EnableGate(_Gate):
    """Enabled while the control signal is positive (enable and action)."""

    type_name = "_EnableGate"
    params_spec = (
        ParamSpec("states", "States when enabling", "held", kind="choice",
                  choices=("held", "reset")),
    )

    def _fresh_mode(self, u):
        # Enabled iff the signal is > 0, i.e. iff −signal is on the negative
        # side under the "zero counts as positive" convention.
        return np.array([0.0 if -self._signal(u) >= 0 else 1.0])

    def zero_crossings(self, t, x, xd, u):
        return np.array([-self._signal(u)])

    @property
    def running(self) -> bool:
        return self._mode is None or bool(self._mode[0] > 0.5)

    def fire(self, ev, t, x, xd) -> bool:
        now = float(self._mode[0]) if self._mode is not None else 1.0
        if self._acted is None or now == self._acted:
            self._acted = now
            return False
        self._acted = now
        if now > 0.5:                                   # enabling
            if self.params["states"] == "reset":
                for plan in self._ordered(ev, self.members):
                    block = plan.block
                    if block.n_states:
                        x[plan.x_slice] = block.initial_continuous_state()
                    if block.n_dstates:
                        xd[plan.xd_slice] = block.initial_discrete_state()
            return True
        values = ev.evaluate(t, x, xd)                  # disabling
        for plan in self._ordered(ev, self.holds):
            hold = plan.block
            xd[plan.xd_slice] = hold.initial_discrete_state() \
                if hold.params["when_disabled"] == "reset" \
                else _width(ev.inputs_for(plan, values)[0], hold.n_dstates)
        return True


@register
class _TriggerGate(_Gate):
    """Runs its members once at each edge of the control signal."""

    type_name = "_TriggerGate"
    params_spec = (
        ParamSpec("edge", "Trigger type", "rising", kind="choice",
                  choices=("rising", "falling", "either")),
    )

    def _fresh_mode(self, u):
        # High iff the signal is > 0, so a 0 → 1 pulse is a rising edge.
        return np.array([0.0 if -self._signal(u) >= 0 else 1.0])

    def zero_crossings(self, t, x, xd, u):
        return np.array([-self._signal(u)])

    def fire(self, ev, t, x, xd) -> bool:
        now = float(self._mode[0]) if self._mode is not None else 0.0
        before, self._acted = self._acted, now
        if before is None or now == before:
            return False
        edge = self.params["edge"]
        rising = now > before
        if not (edge == "either" or (edge == "rising") == rising):
            return False
        values = ev.evaluate(t, x, xd)
        new = xd.copy()
        for plan in self._ordered(ev, self.members):
            if plan.block.n_dstates:
                new[plan.xd_slice] = plan.block.update(
                    t, x[plan.x_slice], xd[plan.xd_slice],
                    ev.inputs_for(plan, values))
        xd[:] = new
        # Like a sample hit: the outputs held until the next edge are the
        # ones after the update.
        values = ev.evaluate(t, x, xd)
        for plan in self._ordered(ev, self.holds):
            xd[plan.xd_slice] = _width(ev.inputs_for(plan, values)[0],
                                       plan.block.n_dstates)
        return True


@register
class _Hold(Block):
    """
    A conditional subsystem's output: the inside's signal while it runs,
    the value it was left at (or its initial output) while it does not.
    """

    type_name = "_Hold"
    category = _HIDDEN
    hidden = True
    params_spec = (
        ParamSpec("when_disabled", "Output when disabled", "held",
                  kind="choice", choices=("held", "reset")),
        ParamSpec("initial", "Initial output", 0.0),
    )

    def configure(self) -> None:
        self._width = 1
        self._gate_obj = None

    def output_widths(self, input_widths):
        self._width = input_widths[0] if input_widths else 1
        return [self._width]

    @property
    def n_dstates(self) -> int:
        return self._width

    def initial_discrete_state(self):
        return np.full(self._width, float(self.params["initial"]))

    def output(self, t, x, xd, u):
        gate = self._gate_obj
        if gate is not None and gate.running:
            return [np.atleast_1d(u[0]) if u else np.zeros(self._width)]
        return [xd.copy()]


def _width(value, n: int) -> np.ndarray:
    v = np.atleast_1d(np.asarray(value, dtype=float))
    return np.resize(v, n) if v.size != n else v


def link_gates(model) -> None:
    """
    Connect the flattened model's gates to the blocks they govern.

    The tags are block ids, carried through every level of flattening; the
    links are object references, made once the model is flat. A triggered
    subsystem may not hold continuous states, as in Simulink.
    """
    from ..compile import CompileError

    gates = {b.block_id: b for b in model if isinstance(b, _Gate)}
    for gate in gates.values():
        gate.members, gate.holds = [], []
    for block in model:
        block._gate_objs = [gates[g] for g in getattr(block, "_gates", ())
                            if g in gates]
        for gate in block._gate_objs:
            gate.members.append(block.block_id)
        hold_gate = getattr(block, "_hold_gate", None)
        if hold_gate is not None and hold_gate in gates:
            block._gate_obj = gates[hold_gate]
            gates[hold_gate].holds.append(block.block_id)
    for gate in gates.values():
        if isinstance(gate, _TriggerGate):
            continuous = [m for m in gate.members if model.block(m).n_states]
            if continuous:
                raise CompileError(
                    f"{', '.join(continuous)}: a triggered subsystem runs "
                    f"only at its trigger's edges, so it cannot hold "
                    f"continuous states. Use discrete blocks inside it, or "
                    f"an enabled subsystem.")
