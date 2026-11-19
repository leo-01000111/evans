"""
The model context bar: what is loaded, and the buttons that change it.

This replaces the permanent 420–760 px left column as the app's answer to
"what am I looking at". That column showed the architecture diagram and a
block editor on *every* tab — 21 % of the window, including on the two tabs
that analyse a different model entirely — while the only always-visible
summary of the system was a status line reading

    G=[1, 2]/[1, 3, 3, 1]   K₂=[4]/[1]

which is a pair of coefficient arrays, not a transfer function, and says
nothing about stability.

The bar shows the factored transfer functions G(s) and K₂(s), a *Plant* menu
(the presets and the systems in the console), *Edit loop* and *Design*. They sit on one
line when both fit beside each other and on two otherwise. A transfer function
too long even for its own line is cut short, with the whole of it in the
tooltip, so a long loop can no longer widen the window.

The verdict (the stability lamp) and the margins are :class:`LoopStatus`,
which the main window puts in the status bar, shown on Analyse. The diagram
and the block editor are the *Loop* tab of the Analyse side panel.
"""

from __future__ import annotations

import control as ctl
import numpy as np
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QPainter, QPalette
from PySide6.QtWidgets import (
    QBoxLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QToolButton,
    QWidget,
)

from ..core.architecture import CourseArchitecture
from ..core.freqresp import bode
from ..core.tf_utils import factored_str
from . import keys
from .design import NORMAL, SECTION, TIGHT, MetricLabel, Status, StatusBadge, monospace


class LoopStatus(QWidget):
    """
    The stability lamp and the headline margins (PM, GM, ωc) of the loop.

    It used to be the middle of the context bar. The main window now keeps it
    in the status bar, as a permanent widget shown on Analyse only; the
    explanation of the verdict is the lamp's tooltip.
    """

    def __init__(self, arch: CourseArchitecture, parent=None) -> None:
        super().__init__(parent)
        self._arch = arch
        self._note = ""
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(SECTION)
        self.setAccessibleName("loop status")

        self._badge = StatusBadge()
        row.addWidget(self._badge)
        self._pm = MetricLabel("PM", "°")
        self._gm = MetricLabel("GM", "dB")
        self._wc = MetricLabel("ωc", "rad/s")
        for metric in (self._pm, self._gm, self._wc):
            row.addWidget(metric)
        self.refresh()

    # ── state ───────────────────────────────────────────────────

    def set_architecture(self, arch: CourseArchitecture) -> None:
        self._arch = arch
        self.refresh()

    def refresh(self, arch: CourseArchitecture | None = None) -> None:
        """
        Recompute the verdict and the margins.

        Guarded by hand rather than with ``@guard``: this is chrome, and a bar
        that replaces itself with an error banner because a margin could not
        be computed is worse than one that says so in its own fields.
        """
        if arch is not None:
            self._arch = arch
        self._refresh_verdict()
        self._refresh_margins()

    def _set_note(self, text: str) -> None:
        self._note = text
        self._badge.setToolTip(text)

    def _refresh_verdict(self) -> None:
        try:
            report = self._arch.internal_stability()
        except Exception as exc:                                # noqa: BLE001
            self._badge.set_status(Status.ERROR, "stability unknown")
            self._set_note(f"{type(exc).__name__}: {exc}")
            return

        if not report.stable:
            worst = max((m.real for m in report.unstable_modes), default=0.0)
            self._badge.set_status(Status.CRITICAL, "unstable")
            hidden = len(report.unstable_hidden)
            self._set_note(
                f"{len(report.unstable_modes)} mode(s) in the right half "
                f"plane, fastest Re = {worst:+.3g}"
                + (f" — {hidden} of them hidden from every port"
                   if hidden else ""))
        elif report.cancellations:
            self._badge.set_status(Status.WARNING, "stable, with cancellation")
            self._set_note(
                f"{len(report.cancellations)} pole–zero cancellation(s); "
                f"the loop is internally stable but a mode is invisible.")
        else:
            self._badge.set_status(Status.OK, "stable")
            self._set_note("")

    def _refresh_margins(self) -> None:
        try:
            data = bode(self._arch.loop_tf())
        except Exception:                                       # noqa: BLE001
            for metric in (self._pm, self._gm, self._wc):
                metric.set_undefined("the loop response could not be computed")
            return

        if np.isfinite(data.wc) and data.wc > 0:
            self._pm.set_value(data.pm_deg, "{:.1f}")
            self._wc.set_value(data.wc)
        else:
            why = ("the loop never crosses 0 dB, so there is no gain "
                   "crossover to measure a phase margin at")
            self._pm.set_undefined(why)
            self._wc.set_undefined(why)

        if np.isfinite(data.gm_dB):
            self._gm.set_value(data.gm_dB, "{:.2f}")
        else:
            self._gm.set_undefined(
                "the phase never reaches −180°, so the gain margin is infinite")

    # ── for tests and callers ───────────────────────────────────

    @property
    def verdict(self) -> Status:
        return self._badge.status

    @property
    def note(self) -> str:
        """Why the verdict is what it is (also the lamp's tooltip)."""
        return self._note

    def summary(self) -> str:
        """The verdict as one line — what a screen reader would announce."""
        return f"{self._badge.text()}  {self._note}".strip()

    def margins(self) -> str:
        return "  ".join(
            f"{metric._name.text()} {metric._value.text()}"
            for metric in (self._pm, self._gm, self._wc))


class _ElidedLabel(QLabel):
    """
    A one-line label that is cut short instead of widening its parent.

    ``text()`` is always the whole string; only the painting is shortened, and
    the tooltip carries the whole of it.
    """

    def setText(self, text: str) -> None:                 # noqa: N802 (Qt API)
        super().setText(text)
        self.setToolTip(text)
        self._sync_interaction()

    def minimumSizeHint(self) -> QSize:                   # noqa: N802
        metrics = self.fontMetrics()
        return QSize(metrics.averageCharWidth() * 14, metrics.height())

    def _elided(self) -> bool:
        return self.fontMetrics().horizontalAdvance(self.text()) > self.width()

    def _sync_interaction(self) -> None:
        # Selecting text that is not drawn would select nothing visible.
        self.setTextInteractionFlags(
            Qt.NoTextInteraction if self._elided()
            else Qt.TextSelectableByMouse)

    def resizeEvent(self, event) -> None:                 # noqa: N802
        super().resizeEvent(event)
        self._sync_interaction()

    def paintEvent(self, event) -> None:                  # noqa: N802
        if not self._elided():
            super().paintEvent(event)
            return
        painter = QPainter(self)
        painter.setFont(self.font())
        painter.setPen(self.palette().color(QPalette.WindowText))
        painter.drawText(
            self.rect(), Qt.AlignLeft | Qt.AlignVCenter,
            self.fontMetrics().elidedText(self.text(), Qt.ElideRight,
                                          self.width()))


class _Systems(QWidget):
    """G(s) and K₂(s): beside each other when they fit, stacked when not."""

    def __init__(self, plant: QLabel, controller: QLabel, parent=None) -> None:
        super().__init__(parent)
        self._plant, self._controller = plant, controller
        self._box = QBoxLayout(QBoxLayout.TopToBottom, self)
        self._box.setContentsMargins(0, 0, 0, 0)
        self._box.setSpacing(0)
        self._box.addWidget(plant)
        self._box.addWidget(controller)
        self._box.addStretch(1)

    @property
    def stacked(self) -> bool:
        return self._box.direction() == QBoxLayout.TopToBottom

    def arrange(self) -> None:
        """Choose one line or two for the room this widget has now."""
        need = (self._plant.sizeHint().width()
                + self._controller.sizeHint().width() + SECTION * 2)
        direction = (QBoxLayout.LeftToRight if need <= self.width()
                     else QBoxLayout.TopToBottom)
        if direction != self._box.direction():
            self._box.setDirection(direction)
            self._box.setSpacing(SECTION * 2 if direction ==
                                 QBoxLayout.LeftToRight else 0)

    def resizeEvent(self, event) -> None:                 # noqa: N802
        super().resizeEvent(event)
        self.arrange()


class ContextBar(QFrame):
    """One strip: the plant, the controller, and the buttons that change them."""

    #: The user asked to see the loop editor (*Edit loop*).
    edit_requested = Signal()
    #: The user asked for the Design tab (*Design*).
    design_requested = Signal()

    def __init__(self, arch: CourseArchitecture, parent=None) -> None:
        super().__init__(parent)
        self._arch = arch
        self.setFrameShape(QFrame.StyledPanel)
        self.setProperty("hp", "panel")      # the DataPlate: 2 px ink frame
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        outer = QHBoxLayout(self)
        outer.setContentsMargins(SECTION, TIGHT, SECTION, TIGHT)
        outer.setSpacing(SECTION)

        # ── the systems ──
        self._plant = _ElidedLabel("")
        self._plant.setFont(monospace())
        self._plant.setAccessibleName("plant transfer function")
        self._controller = _ElidedLabel("")
        self._controller.setFont(monospace())
        self._controller.setAccessibleName("controller transfer function")
        self._systems = _Systems(self._plant, self._controller)
        outer.addWidget(self._systems, stretch=1)

        # ── the verdict and margins live in the status bar ──
        self.status = LoopStatus(arch)

        outer.addWidget(_divider())

        # The menu is the main window's (set_plant_menu): the presets, and
        # the systems in the console's workspace.
        self._plant_btn = QToolButton()
        self._plant_btn.setText("Plant")
        self._plant_btn.setPopupMode(QToolButton.InstantPopup)
        self._plant_btn.setToolTip(
            "Load a preset plant, or a system from the console workspace, "
            "as G(s)")
        self._plant_btn.setAccessibleName("Plant")
        outer.addWidget(self._plant_btn)

        self._edit_btn = QPushButton("Edit loop")
        self._edit_btn.setToolTip(keys.label(
            "Open the side panel on Loop: the architecture diagram and the "
            "block editor (Ctrl+\\)"))
        self._edit_btn.setAccessibleName("Edit loop")
        self._edit_btn.clicked.connect(self.edit_requested)
        outer.addWidget(self._edit_btn)

        self._design_btn = QPushButton("Design")
        self._design_btn.setToolTip(keys.label(
            "Open the side panel on Design: gain, compensator and PID "
            r"(Ctrl+\)"))
        self._design_btn.setAccessibleName("Design")
        self._design_btn.clicked.connect(self.design_requested)
        outer.addWidget(self._design_btn)

        self.refresh()

    # ── state ───────────────────────────────────────────────────

    def set_plant_menu(self, menu) -> None:
        """The menu behind the *Plant* button."""
        self._plant_btn.setMenu(menu)

    def set_architecture(self, arch: CourseArchitecture) -> None:
        self._arch = arch
        self.status.set_architecture(arch)
        self.refresh()

    def refresh(self, *_ignored) -> None:
        """Recompute the summary (and the status bar's verdict with it)."""
        try:
            self._plant.setText(f"G(s)  = {factored_str(self._arch.block_tf('G'))}")
            self._controller.setText(
                f"K₂(s) = {factored_str(self._arch.block_tf('K2'))}")
        except Exception as exc:                                # noqa: BLE001
            self._plant.setText("G(s)  = —")
            self._controller.setText(f"K₂(s) = — ({type(exc).__name__})")
        self._systems.arrange()
        self.status.refresh(self._arch)

    # ── for tests and callers ───────────────────────────────────

    def describe(self) -> str:
        """The summary and the margins, as text (what Cedric reads)."""
        return f"{self.summary()}  {self.status.margins()}".strip()

    @property
    def verdict(self) -> Status:
        return self.status.verdict

    @property
    def stacked(self) -> bool:
        """Whether G and K₂ are on two lines (they do not fit on one)."""
        return self._systems.stacked

    def summary(self) -> str:
        """The whole bar as one line — what a screen reader would announce."""
        return (f"{self._plant.text()}  {self._controller.text()}  "
                f"{self.status.summary()}").strip()


def _divider() -> QFrame:
    line = QFrame()
    line.setProperty("hp", "rule")      # a 1 px rule, drawn by the stylesheet
    line.setContentsMargins(NORMAL, 0, NORMAL, 0)
    return line


def short_tf(tf: ctl.TransferFunction, limit: int = 46) -> str:
    """A factored transfer function, elided if it will not fit."""
    text = factored_str(tf)
    return text if len(text) <= limit else text[: limit - 1] + "…"
