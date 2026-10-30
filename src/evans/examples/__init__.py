"""
Example Simulink models, opened from File ▸ Examples.

Each is a ``.fmdl`` file beside this module, built by
``tools/build_examples.py`` from the course's own systems, so the files can
be rebuilt after a format change rather than edited by hand. Every one runs
as it opens: no workspace variables to define first.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

FOLDER = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Example:
    file: str
    title: str
    summary: str

    @property
    def path(self) -> Path:
        return FOLDER / self.file


EXAMPLES = (
    Example("dc_motor.fmdl", "DC motor speed control",
            "A PID holding a DC motor's speed, its voltage limited to ±12 V."),
    Example("cruise_control.fmdl", "Cruise control",
            "A PI controller on a car's speed, with the engine force limited."),
    Example("inverted_pendulum.fmdl", "Inverted pendulum",
            "A pendulum held upright by a PD controller; the nonlinear "
            "dynamics are an Fcn block."),
    Example("pid_saturation.fmdl", "PID with a saturating actuator",
            "Integrator windup, and the same loop with anti-windup beside it."),
)


def examples() -> tuple[Example, ...]:
    """The examples that are present, in menu order."""
    return tuple(e for e in EXAMPLES if e.path.is_file())
