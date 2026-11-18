"""
The Design tab of the Analyse side panel: Gain · Compensator · PID.

What were two docked apps (the Control System Designer and the PID Tuner)
are now three views in the side panel, and they no longer draw their own
Bode and step plots: the pane grid is the display. A change applies at once,
through `MainWindow.change_loop`, so every pane moves with the slider and one
drag is one undo step.

Three rules keep it honest:

- **Live, but throttled.** While a slider or the pole target is held, K₂ is
  written at most every `APPLY_INTERVAL_MS`; on release it is written once
  more. Each gesture gets its own merge key, so a drag is one undo step and
  the next drag is another.
- **It follows the loop.** When the loop changes from anywhere else (an
  undo, a preset, the Loop tab, the console), `loop_changed` re-reads G, H
  and K₂ into the widgets. Its own writes come back through the same path,
  so `_applying` is checked first and they are not re-read (which would move
  a slider under the user's hand).
- **Reset** puts back the K₂ the tab found when it was shown.
"""

from __future__ import annotations

from collections.abc import Callable

import control as ctl
from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ..core.architecture import CourseArchitecture
from ..core.designer import Compensator
from .apps.designer_app import ControlSystemDesigner
from .apps.pid_tuner import PIDTuner
from .design import NORMAL, TIGHT

#: At most one write to the loop per this many ms while something is held.
APPLY_INTERVAL_MS = 50

#: The three views, in the order the segmented control shows them.
MODES = ("gain", "compensator", "pid")
_TITLES = {"gain": "Gain", "compensator": "Compensator", "pid": "PID"}
_UNDO_TEXT = {"gain": "Design: gain", "compensator": "Design: compensator",
              "pid": "Design: PID"}

#: ``apply(text, tf, merge_key)``: write ``tf`` into K₂ as one undo step.
ApplyFn = Callable[[str, ctl.TransferFunction, "str | None"], None]


def _compensator_of(tf) -> Compensator:
    """K₂ in the designer's zero-pole-gain form, or a gain of 1 if not."""
    try:
        return Compensator.from_tf(tf)
    except Exception:                               # noqa: BLE001
        return Compensator()


class DesignPanel(QWidget):
    """Gain, compensator and PID design over the shared loop."""

    #: The view now showing: "gain", "compensator" or "pid".
    mode_changed = Signal(str)

    def __init__(self, arch: CourseArchitecture, apply: ApplyFn,
                 parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("designPanel")
        self.setAccessibleName("Design")
        self._arch = arch
        self._apply_fn = apply
        #: Set while this tab writes K₂, so the re-read it triggers is skipped.
        self._applying: str | None = None
        #: The halves that missed a loop change; re-read when next shown.
        self._stale: set[str] = set()
        #: K₂ as found when the tab was shown: what Reset goes back to.
        self._reset_to = arch.block_tf("K2")
        #: Each gesture gets its own merge key, so two drags are two steps.
        self._gesture = 0
        self._pending: str | None = None

        self._throttle = QTimer(self)
        self._throttle.setSingleShot(True)
        self._throttle.setInterval(APPLY_INTERVAL_MS)
        self._throttle.timeout.connect(self._flush)

        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(NORMAL)

        # ── the segmented control ──
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        self._modes = QButtonGroup(self)
        self._modes.setExclusive(True)
        self._mode_buttons: dict[str, QPushButton] = {}
        for mode in MODES:
            button = QPushButton(_TITLES[mode])
            button.setCheckable(True)
            button.setAccessibleName(f"{_TITLES[mode]} design")
            button.setToolTip({
                "gain": "Drag a closed-loop pole along the root locus",
                "compensator": "Place the compensator's zeros and poles",
                "pid": "Tune a PID from two targets",
            }[mode])
            button.clicked.connect(
                lambda _checked=False, m=mode: self.set_mode(m))
            self._modes.addButton(button)
            self._mode_buttons[mode] = button
            row.addWidget(button, stretch=1)
        column.addLayout(row)

        # ── the views, built when first shown ──
        # Not at construction: a root locus and a PID tune cost a quarter of
        # a second, and the window is built at every launch.
        self._stack = QStackedWidget()
        self._designer: ControlSystemDesigner | None = None
        self._tuner: PIDTuner | None = None
        column.addWidget(self._stack)

        bottom = QHBoxLayout()
        bottom.setContentsMargins(0, 0, 0, 0)
        bottom.setSpacing(TIGHT)
        self._reset_btn = QPushButton("Reset")
        self._reset_btn.setAccessibleName("Reset the controller")
        self._reset_btn.setToolTip(
            "Back to the controller from before this tab was opened")
        self._reset_btn.clicked.connect(self.reset)
        bottom.addWidget(self._reset_btn)
        bottom.addStretch(1)
        column.addLayout(bottom)
        column.addStretch(1)

        self._mode = "gain"
        self._mode_buttons["gain"].setChecked(True)

    # ── views ───────────────────────────────────────────────────

    @property
    def designer(self) -> ControlSystemDesigner:
        """Gain and Compensator: one root-locus designer, two views."""
        if self._designer is None:
            arch = self._arch
            self._designer = ControlSystemDesigner(
                plant=arch.block_tf("G"),
                compensator=_compensator_of(arch.block_tf("K2")),
                sensor=arch.block_tf("H"))
            self._designer.changed.connect(self._on_designer_changed)
            self._stack.addWidget(self._designer)
            self._stale.discard("designer")
        return self._designer

    @property
    def tuner(self) -> PIDTuner:
        """PID."""
        if self._tuner is None:
            arch = self._arch
            self._tuner = PIDTuner(plant=arch.block_tf("G"),
                                   sensor=arch.block_tf("H"),
                                   feedforward=arch.block_tf("K1"))
            self._tuner.changed.connect(self._on_tuner_changed)
            self._stack.addWidget(self._tuner)
            self._stale.discard("tuner")
        return self._tuner

    @property
    def mode(self) -> str:
        return self._mode

    def set_mode(self, mode: str) -> None:
        """Show Gain, Compensator or PID."""
        if mode not in MODES:
            raise ValueError(f"unknown design view {mode!r}")
        self._mode_buttons[mode].setChecked(True)
        if mode == "pid":
            self._stack.setCurrentWidget(self.tuner)
        else:
            self._stack.setCurrentWidget(self.designer)
            self.designer.set_view(mode)
        changed = mode != self._mode
        self._mode = mode
        self._refresh_stale()
        if changed:
            self.mode_changed.emit(mode)

    def _built(self, half: str):
        return self._designer if half == "designer" else self._tuner

    def _half(self, mode: str) -> str:
        return "tuner" if mode == "pid" else "designer"

    # ── the loop changed ────────────────────────────────────────

    def loop_changed(self) -> None:
        """
        The loop changed. From this tab: the *other* half is now stale.
        From anywhere else: re-read the loop into the widgets.
        """
        if self._applying is not None:
            self._stale |= {"designer", "tuner"} - {self._half(
                self._applying)}
            return
        self._stale = {"designer", "tuner"}
        self._refresh_stale()

    def _refresh_stale(self) -> None:
        """Re-read the loop into the half in view, if it missed a change."""
        if not self.isVisible():
            return                                  # on the next show
        half = self._half(self._mode)
        if half not in self._stale or self._built(half) is None:
            return
        self._stale.discard(half)
        arch = self._arch
        if half == "designer":
            self.designer.set_plant(arch.block_tf("G"), arch.block_tf("H"),
                                    _compensator_of(arch.block_tf("K2")))
        else:
            self.tuner.set_plant(arch.block_tf("G"),
                                 sensor=arch.block_tf("H"),
                                 feedforward=arch.block_tf("K1"))

    def showEvent(self, event) -> None:              # noqa: N802 (Qt API)
        super().showEvent(event)
        if not event.spontaneous():
            self._reset_to = self._arch.block_tf("K2")
        if self._built(self._half(self._mode)) is None:
            self.set_mode(self._mode)               # builds the view in sight
        self._refresh_stale()

    # ── writing K₂ ──────────────────────────────────────────────

    def _on_designer_changed(self, what: str, final: bool) -> None:
        self._queue(what, final)

    def _on_tuner_changed(self, final: bool) -> None:
        self._queue("pid", final)

    def _queue(self, what: str, final: bool) -> None:
        """Apply now if the gesture is over, else at most every 50 ms."""
        if self._pending is not None and self._pending != what:
            self._flush()
        self._pending = what
        if final:
            self._throttle.stop()
            self._flush()
            self._gesture += 1
        elif not self._throttle.isActive():
            self._throttle.start()

    def _flush(self) -> None:
        what, self._pending = self._pending, None
        if what is None:
            return
        tf = self._controller(what)
        if tf is None:
            return
        self._applying = what
        try:
            self._apply_fn(_UNDO_TEXT[what], tf,
                           f"design-{what}/{self._gesture}")
        finally:
            self._applying = None

    def _controller(self, what: str):
        if what == "pid":
            result = self.tuner.result
            if result is None or not result.feasible:
                return None
            return result.C
        return self.designer.compensator.tf()

    def reset(self) -> None:
        """Put back the K₂ this tab found when it was shown."""
        self._throttle.stop()
        self._pending = None
        self._gesture += 1
        # Not under `_applying`: the widgets must follow K₂ back.
        self._apply_fn("Design: reset", self._reset_to, None)
