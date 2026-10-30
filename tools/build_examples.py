"""
Write the example models in src/evans/examples/.

    python tools/build_examples.py

The models are built here in code, so a change to the file format or to a
block's parameters means running this again rather than editing JSON. Each
one is simulated before it is saved, and the script stops if a run fails.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from evans.examples import FOLDER  # noqa: E402
from evans.sim import SimModel, simulate  # noqa: E402

#: Blocks 220 px apart, centre to centre: each wire gets a clear run.
STEP = 220


def dc_motor() -> SimModel:
    """
    The DC motor of the control tutorials: J = 0.01, b = 0.1, K = 0.01,
    R = 1, L = 0.5, so speed over voltage is
    K / ((Js + b)(Ls + R) + K²) = 0.01 / (0.005 s² + 0.06 s + 0.1001).
    """
    m = SimModel("dc_motor")
    m.settings.update(StopTime=3.0)
    m.add("Step", "r", x=-2 * STEP, y=0, step_time=0.0, final=1.0)
    m.add("Sum", "e", x=-STEP, y=0, signs="+-")
    m.add("PID", "C", x=0, y=0, Kp=100.0, Ki=200.0, Kd=10.0, Tf=0.01)
    m.add("Saturation", "V", x=STEP, y=0, upper=12.0, lower=-12.0)
    m.add("TransferFcn", "G", x=2 * STEP, y=0, num="0.01",
          den="0.005, 0.06, 0.1001")
    m.add("Scope", "speed", x=3 * STEP, y=0, title="Speed")
    m.connect("r", "e.in1")
    m.connect("e", "C")
    m.connect("C", "V")
    m.connect("V", "G")
    m.connect("G", "e.in2")
    m.connect("G", "speed")
    m.signal_names = {"G.out": "speed (rad/s)", "V.out": "voltage (V)"}
    m.annotations.append({
        "text": "PID from the DC motor tutorial; the supply limits the "
                "voltage to ±12 V.", "x": -2 * STEP, "y": -110})
    return m


def cruise_control() -> SimModel:
    """A 1000 kg car with 50 N·s/m of drag: v' = (u − 50 v) / 1000."""
    m = SimModel("cruise_control")
    m.settings.update(StopTime=40.0)
    m.add("Step", "r", x=-2 * STEP, y=0, step_time=1.0, final=10.0)
    m.add("Sum", "e", x=-STEP, y=0, signs="+-")
    m.add("PID", "C", x=0, y=0, Kp=800.0, Ki=40.0, Kd=0.0)
    m.add("Saturation", "F", x=STEP, y=0, upper=3000.0, lower=-3000.0)
    m.add("TransferFcn", "G", x=2 * STEP, y=0, num="1", den="1000, 50")
    m.add("ToWorkspace", "v", x=3 * STEP, y=0, name="speed",
          format="Array")
    m.connect("r", "e.in1")
    m.connect("e", "C")
    m.connect("C", "F")
    m.connect("F", "G")
    m.connect("G", "e.in2")
    m.connect("G", "v")
    m.signal_names = {"G.out": "speed (m/s)", "F.out": "force (N)"}
    m.annotations.append({
        "text": "Engine force limited to ±3000 N. After a run, the speed is "
                "out.speed at the console.", "x": -2 * STEP, "y": -110})
    return m


def inverted_pendulum() -> SimModel:
    """
    A unit pendulum (m = l = 1) about its upright position:
    θ'' = g·sin θ − 0.1·θ' + τ, with τ = −(40 θ + 10 θ') from a PD.
    Starts 0.2 rad off vertical.
    """
    m = SimModel("inverted_pendulum")
    m.settings.update(StopTime=5.0)
    m.add("Mux", "mx", x=-STEP, y=0, n_inputs=3)
    m.add("Fcn", "f", x=0, y=0,
          expr="9.81*sin(u(1)) - 0.1*u(2) + u(3)")
    m.add("Integrator", "w", x=STEP, y=0, x0=0.0)
    m.add("Integrator", "th", x=2 * STEP, y=0, x0=0.2)
    m.add("Gain", "Kp", x=STEP, y=180, gain=-40.0)
    m.add("Gain", "Kd", x=2 * STEP, y=180, gain=-10.0)
    m.add("Sum", "tau", x=0, y=180, signs="++")
    m.add("XYGraph", "phase", x=3 * STEP, y=90, title="Phase portrait")
    for name in ("Kp", "Kd", "tau"):
        m.orient(name, flip=True)
    m.connect("th", "mx.in1")
    m.connect("w", "mx.in2")
    m.connect("tau", "mx.in3")
    m.connect("mx", "f")
    m.connect("f", "w")
    m.connect("w", "th")
    m.connect("th", "Kp")
    m.connect("w", "Kd")
    m.connect("Kp", "tau.in1")
    m.connect("Kd", "tau.in2")
    m.connect("th", "phase.x")
    m.connect("w", "phase.y")
    m.signal_names = {"th.out": "θ (rad)", "w.out": "ω (rad/s)",
                      "tau.out": "τ"}
    m.annotations.append({
        "text": "θ'' = g·sin θ − 0.1 θ' + τ, upright at θ = 0. The scope's "
                "view menu shows the phase portrait.",
        "x": -STEP, "y": -110})
    return m


def pid_saturation() -> SimModel:
    """
    The plant 1/(s+1)² under a PI controller (Kp = 2, Ki = 4) whose output is
    clipped to ±1.5, twice over. On top the clip follows the controller and
    its integrator winds up. Below, the PI is built from blocks and its
    Integrator is limited, so that the integral stops at the same bounds
    and has nothing to unwind.
    """
    m = SimModel("pid_saturation")
    m.settings.update(StopTime=20.0)
    m.add("Step", "r", x=-2 * STEP, y=100, step_time=0.0, final=1.0)

    # Windup: PI, then the clip.
    m.add("Sum", "e_w", x=-STEP, y=0, signs="+-")
    m.add("PID", "C_w", x=0, y=0, Kp=2.0, Ki=4.0, Kd=0.0)
    m.add("Saturation", "u_w", x=STEP, y=0, upper=1.5, lower=-1.5)
    m.add("TransferFcn", "G_w", x=2 * STEP, y=0, num="1", den="1, 2, 1")
    m.connect("r", "e_w.in1")
    m.connect("e_w", "C_w")
    m.connect("C_w", "u_w")
    m.connect("u_w", "G_w")
    m.connect("G_w", "e_w.in2")

    # Anti-windup: Kp·e + Ki·∫e, the integral limited to the clip's range.
    y = 300
    m.add("Sum", "e_a", x=-STEP, y=y, signs="+-")
    m.add("Gain", "Kp_a", x=0, y=y - 60, gain=2.0)
    m.add("Gain", "Ki_a", x=0, y=y + 60, gain=4.0)
    m.add("Integrator", "I_a", x=STEP, y=y + 60, limit=True, upper=1.5,
          lower=-1.5)
    m.add("Sum", "pi_a", x=2 * STEP, y=y, signs="++")
    m.add("Saturation", "u_a", x=3 * STEP, y=y, upper=1.5, lower=-1.5)
    m.add("TransferFcn", "G_a", x=4 * STEP, y=y, num="1", den="1, 2, 1")
    m.connect("r", "e_a.in1")
    m.connect("e_a", "Kp_a")
    m.connect("e_a", "Ki_a")
    m.connect("Ki_a", "I_a")
    m.connect("Kp_a", "pi_a.in1")
    m.connect("I_a", "pi_a.in2")
    m.connect("pi_a", "u_a")
    m.connect("u_a", "G_a")
    m.connect("G_a", "e_a.in2")
    m.signal_names = {"G_w.out": "windup", "G_a.out": "anti-windup"}
    m.annotations.append({
        "text": "Top: the clip after the PI; its integrator winds up and the "
                "output overshoots. Bottom: the integral is limited to the "
                "clip's range, so it does not.",
        "x": -2 * STEP, "y": -120})
    return m


BUILDERS = {
    "dc_motor.fmdl": dc_motor,
    "cruise_control.fmdl": cruise_control,
    "inverted_pendulum.fmdl": inverted_pendulum,
    "pid_saturation.fmdl": pid_saturation,
}


def main() -> None:
    for file, build in BUILDERS.items():
        model = build()
        result = simulate(model, t_end=float(model.settings["StopTime"]))
        model.save(FOLDER / file)
        print(f"{file}: {len(model)} blocks, {len(result.t)} samples")


if __name__ == "__main__":
    main()
