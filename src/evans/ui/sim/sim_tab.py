"""
The Simulink tab: palette · canvas · scope, plus a run toolbar.

The run happens on a worker thread. A stiff model or a long run can take
seconds, and a frozen window during a simulation is indistinguishable from a
crashed one — so the UI stays live, shows progress, and can be cancelled.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import (
    QEvent,
    QObject,
    QSettings,
    QSize,
    Qt,
    QThread,
    QTimer,
    Signal,
)
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QProxyStyle,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStyle,
    QToolBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ...sim.compile import CompileError, compile_model
from ...sim.linearize import LinearizationError, linearize, steady_state
from ...sim.model import LEGACY_SUFFIX, SUFFIX, ModelError, PortRef, SimModel
from ...sim.scripts import (
    BEFORE_RUN,
    ON_OPEN,
    WHEN_TEXT,
    ScriptError,
    due,
    needs_trust,
    path_key,
    run_scripts,
)
from ...sim.solver import SimulationError, resolve_solver, simulate
from ...sim.workspace import resolve_model
from .. import iconset, keys, persist, theme
from ..design import NORMAL, TIGHT
from ..guard import GuardedPanel, guard
from ..unsaved import ask_to_save, marked
from .arrange import ArrangePanel, hidden_actions
from .canvas import SimCanvas
from .inspector import BlockInspector
from .palette import STRIP_WIDTH, PaletteDock
from .scope import ScopeWidget
from .scope_window import ScopeWindow

#: The solver combo, group by group with a separator between: Simulink's
#: variable-step names, the fixed-step ones, then the scipy names they map to.
SOLVER_MENU = (
    ["ode45", "ode23", "ode15s", "ode23s", "ode23t", "ode113"],
    ["ode1", "ode2", "ode3", "ode4", "ode5"],
    ["RK45", "RK23", "DOP853", "LSODA", "Radau", "BDF"],
)


class _Worker(QObject):
    """Runs one simulation off the GUI thread."""

    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(float)

    def __init__(self, model: SimModel, options: dict) -> None:
        super().__init__()
        self.model = model
        self.options = options
        self.cancelled = False

    def run(self) -> None:
        def tick(fraction: float) -> None:
            self.progress.emit(fraction)
            if self.cancelled:
                raise SimulationError("cancelled")

        try:
            self.finished.emit(simulate(self.model, progress=tick,
                                        **self.options))
        except (SimulationError, CompileError, ModelError, ValueError) as exc:
            self.failed.emit(str(exc))
        except Exception as exc:                       # noqa: BLE001
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class _OverflowStyle(QProxyStyle):
    """The toolbar's style, with room for a labelled "More" button."""

    #: Wide enough for "MORE" in the sign font, with its padding.
    EXTENT = 64

    def pixelMetric(self, metric, option=None, widget=None):  # noqa: N802
        if metric == QStyle.PM_ToolBarExtensionExtent:
            return self.EXTENT
        return super().pixelMetric(metric, option, widget)


def _labelled(text: str, control: QWidget) -> QWidget:
    """A toolbar-sized ``label [control]`` pair that can be hidden as a unit."""
    holder = QWidget()
    row = QHBoxLayout(holder)
    row.setContentsMargins(TIGHT, 0, 0, 0)
    row.setSpacing(TIGHT)
    caption = QLabel(text)
    caption.setStyleSheet("color: palette(mid);")
    row.addWidget(caption)
    row.addWidget(control)
    return holder



class _StatusLine(QLabel):
    """A one-line status that keeps its whole text as its tooltip."""

    def setText(self, text: str) -> None:  # noqa: N802 (Qt's name)
        super().setText(text)
        self.setToolTip(text)

class SimTab(QWidget, GuardedPanel):
    """Model, run, inspect."""

    #: Emitted when the user linearises a model — the analysis tabs pick it up.
    linearised = Signal(object, str)       # TransferFunction, description
    #: A model file was opened or saved — the recent-files list listens.
    file_used = Signal(object)             # Path
    #: A run finished; the console writes it to the workspace as ``out``.
    simulated = Signal(object)             # SimResult

    #: Where the palette's folded/unfolded state is remembered.
    SETTINGS_ORG = "Evans"
    SETTINGS_APP = "Evans"

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: _Worker | None = None
        self._result = None
        self._build_ui()
        # Quitting mid-simulation must stop the solver thread first: Qt
        # aborts the whole process if a QThread is destroyed while running.
        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.shutdown)
        self._load_default_model()

    # ── UI ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(2)
        self.install_error_banner(root)
        root.addWidget(self._build_toolbar())

        splitter = QSplitter(Qt.Horizontal)

        # The dock owns the width rules (a preferred width, not a floor — a
        # 180 px minimum here was one of the constraints that stopped the
        # window being narrowed) and folds away to a strip on request.
        self._palette_dock = PaletteDock()
        self._palette = self._palette_dock.palette
        self._splitter = splitter
        self._palette_width = 200
        splitter.addWidget(self._palette_dock)

        centre = QSplitter(Qt.Vertical)
        self._canvas = SimCanvas()
        centre.addWidget(self._canvas)
        self._arrange = ArrangePanel(self._canvas, self._align,
                                     self._distribute)
        # The global scope: every logged signal, folded away behind a button
        # until asked for. A Scope block's own window (double-click it) is
        # the usual way to look at a run.
        self._centre = centre
        self._scope = ScopeWidget()
        # Its toggle sits under the inspector, not in a bar of its own under
        # the canvas, so a folded-away scope costs the diagram no height.
        self._global = self._scope
        self._global_button = QToolButton()
        self._global_button.setCheckable(True)
        self._global_button.setAutoRaise(True)
        self._global_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self._global_button.setToolTip(
            "Every signal the run logged, in one plot. Double-click a Scope "
            "block for its own window.")
        self._global_button.toggled.connect(self.set_global_scope_visible)
        centre.addWidget(self._global)
        centre.setCollapsible(1, False)
        centre.setStretchFactor(0, 3)
        centre.setStretchFactor(1, 2)
        splitter.addWidget(centre)
        #: Each open Scope block window, by the block's path.
        self._scope_windows: dict[str, ScopeWindow] = {}

        # The inspector, so parameters can be edited with the diagram still
        # visible. They used to be a modal dialog on double-click: you could
        # not see the block you were editing, or compare two of them.
        self._inspector = BlockInspector()
        self._inspector.setMinimumWidth(0)
        side = QWidget()
        side.setMinimumWidth(0)
        side.setMaximumWidth(340)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.setSpacing(2)
        side_layout.addWidget(self._inspector, stretch=1)
        side_layout.addWidget(self._global_button, alignment=Qt.AlignLeft)
        splitter.addWidget(side)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter, stretch=1)

        # The status line and the model's file (marked when the diagram
        # differs from it, as the Live tab shows its script's). They live in
        # the main window's status bar while this page shows
        # (``status_widgets``), not in a row of their own under the canvas.
        self._status = _StatusLine()
        # One line that never widens the window; the full text is the tip.
        self._status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self._file_label = QLabel("")
        self._file_label.setStyleSheet("color: palette(mid);")

        self._palette.block_chosen.connect(self._canvas.add_block)
        self._canvas.status.connect(self._status.setText)
        self._canvas.model_changed.connect(self._on_model_changed)
        self._canvas.model_replaced.connect(self._settings_from_model)
        self._canvas.path_changed.connect(self._on_path_changed)
        self._canvas.selection_changed.connect(self._on_block_selected)
        self._inspector.apply_requested.connect(self._apply_params)
        self._inspector.tune_requested.connect(
            lambda block_id: self._canvas.tune_pid(block_id))
        self._palette_dock.toggled.connect(self._on_palette_toggled)
        self._canvas.scope_requested.connect(self.open_scope_window)
        self._canvas.model_replaced.connect(self.close_scope_windows)
        self._show_global_scope(persist.global_scope_open())
        self._restoring_palette = False
        self._restore_palette_state()
        #: The model as its file holds it (None: unsaved whatever it is).
        self._saved_state: str | None = None
        self.mark_saved()
        #: The file the model on the canvas came from or was last saved to;
        #: None for the starter, an example, or one the console put there.
        self._path: Path | None = None
        #: Whether this .fmdl's first Save has offered the new format.
        self._format_asked = False
        # Any other model on the canvas is not that file's.
        self._canvas.model_replaced.connect(self._forget_path)
        #: The console that runs model scripts (None: scripts cannot run),
        #: and where it looks for a script named without a folder.
        self._script_console = None
        self._script_search = list
        #: Untrusted models whose scripts the user let run this session.
        self._allowed_once: set[str] = set()
        self._show_unsaved()

    def _build_toolbar(self) -> QWidget:
        """
        A real ``QToolBar``, which is the whole point.

        This used to be one ``QHBoxLayout`` holding Run, Stop, stop time,
        solver, step, undo, redo, fit, up, a breadcrumb, Linearise, a progress
        bar and two file buttons — in a row that could not wrap. It demanded
        **1602 px**, and because a tab bar is as wide as its widest tab, that
        one row set the minimum width of the entire application at 2038 px:
        wider than a 1920 monitor, for someone who only wanted a Bode plot.

        A toolbar with ``setMovable(False)`` and overflow puts whatever does
        not fit behind a ``»`` button instead of pushing the window wider.
        Groups are separated the way the plan describes: run, settings,
        history, navigation, bridge, file.
        """
        bar = QToolBar()
        bar.setMovable(False)
        bar.setFloatable(False)
        bar.setIconSize(QSize(16, 16))
        bar.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        bar.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        # ── the block palette ──
        # First, and checkable, so the state it shows is the state of the
        # palette: unchecked means folded away, and one click brings it back.
        self._palette_action = bar.addAction("Blocks")
        iconset.bind(self._palette_action, "blocks")
        self._palette_action.setCheckable(True)
        self._palette_action.setChecked(True)
        self._palette_action.setShortcut("Ctrl+B")
        self._palette_action.setToolTip(
            keys.label("Show or hide the block palette (Ctrl+B)"))
        self._palette_action.triggered.connect(
            lambda checked: self.set_palette_visible(checked))
        bar.addSeparator()

        # ── file ──
        # Near the start: a toolbar that runs out of room hides its *last*
        # entries, and at the end these were the ones a narrow window lost.
        for label, icon, slot, tip in (
            ("Open…", "open", self.open_model, "Open a model (.evx or .fmdl)"),
            ("Save", "save", self.save_model, "Save this model to its file"),
            ("Save As…", "save", self.save_model_as,
             "Save this model to a new file (.evx, or .fmdl for an older "
             "Evans)"),
        ):
            action = bar.addAction(label)
            iconset.bind(action, icon)
            action.setToolTip(tip)
            action.triggered.connect(slot)
        self._scripts_action = bar.addAction("Scripts…")
        iconset.bind(self._scripts_action, "edit")
        self._scripts_action.setToolTip(
            "Model scripts: .m files this model runs when it opens and "
            "before every run, to set the variables its blocks use")
        self._scripts_action.triggered.connect(self.edit_model_scripts)
        bar.addSeparator()

        # ── run ──
        self._run_btn = QPushButton("Run")
        iconset.bind(self._run_btn, "run")
        self._run_btn.setShortcut("Ctrl+R")
        self._run_btn.setToolTip(keys.label("Run the simulation (Ctrl+R)"))
        self._run_btn.clicked.connect(self.run_simulation)
        bar.addWidget(self._run_btn)

        self._stop_btn = QPushButton("Stop")
        iconset.bind(self._stop_btn, "stop", "hold_ink")
        self._stop_btn.setEnabled(False)
        self._stop_btn.setToolTip("Cancel the running simulation")
        self._stop_btn.clicked.connect(self._cancel)
        bar.addWidget(self._stop_btn)
        bar.addSeparator()

        # ── simulation settings ──
        self._t_end = QDoubleSpinBox()
        self._t_end.setRange(1e-3, 1e6)
        self._t_end.setValue(10.0)
        self._t_end.setDecimals(3)
        self._t_end.setAccessibleName("stop time")
        self._t_end.setToolTip("Stop time (s)")
        self._t_end.valueChanged.connect(
            lambda v: self._store_setting("StopTime", float(v)))
        bar.addWidget(_labelled("Stop", self._t_end))

        # Simulink's names first, since that is what people type; the scipy
        # names stay below a separator, so an old habit (or a script that
        # sets "RK45") still finds its entry.
        self._solver = QComboBox()
        self._solver.addItems(SOLVER_MENU[0])
        for group in SOLVER_MENU[1:]:
            self._solver.insertSeparator(self._solver.count())
            self._solver.addItems(group)
        self._solver.setAccessibleName("solver")
        self._solver.currentTextChanged.connect(
            lambda text: self._store_setting("Solver", text))
        self._solver.setToolTip(
            "ode45 is a good default. ode15s or ode23s for stiff models "
            "(widely separated time constants); ode113 for tight tolerances. "
            "ode1–ode5 are fixed-step (Euler to Dormand–Prince), for matching "
            "what an embedded controller will do — they need a Step. "
            "Below the second line are the same methods by their scipy names.")
        bar.addWidget(_labelled("Solver", self._solver))

        self._step = QDoubleSpinBox()
        self._step.setRange(0.0, 1e3)
        self._step.setDecimals(5)
        self._step.setValue(0.0)
        self._step.setSpecialValueText("auto")
        self._step.setAccessibleName("maximum step")
        self._step.setToolTip(
            "Maximum step; required for the fixed-step solvers.")
        self._step.valueChanged.connect(
            lambda v: self._store_setting("MaxStep", float(v)))
        bar.addWidget(_labelled("Step", self._step))
        bar.addSeparator()

        # ── history ──
        # Fit, Align and Space are not here: they are the arrange panel over
        # the canvas's corner (see arrange.py).
        undo = bar.addAction("Undo")
        iconset.bind(undo, "undo")
        undo.setToolTip(keys.label("Undo (Ctrl+Z)"))
        undo.setShortcut("Ctrl+Z")
        undo.triggered.connect(lambda: self._canvas.undo_stack.undo())
        redo = bar.addAction("Redo")
        iconset.bind(redo, "redo")
        redo.setToolTip(keys.label("Redo (Ctrl+Y)"))
        redo.setShortcut("Ctrl+Y")
        redo.triggered.connect(lambda: self._canvas.undo_stack.redo())
        bar.addSeparator()

        # ── subsystem navigation ──
        self._up_action = bar.addAction("Up")
        iconset.bind(self._up_action, "ascend")
        self._up_action.setToolTip("Leave this subsystem (Esc)")
        self._up_action.triggered.connect(lambda: self._canvas.ascend())
        self._up_action.setVisible(False)

        self._crumb = QLabel("")
        self._crumb.setStyleSheet("color: palette(mid);")
        bar.addWidget(self._crumb)
        bar.addSeparator()

        # ── the bridge to the analysis tabs ──
        lin = bar.addAction("Linearise")
        iconset.bind(lin, "linearise")
        lin.setToolTip("Linearise the model and send it to the analysis tabs")
        lin.triggered.connect(self.linearise)

        # The progress bar lives outside the toolbar: it appears and vanishes,
        # and a toolbar that reflows every time a simulation starts is worse
        # than one that does not.
        self._progress = QProgressBar()
        self._progress.setMaximumWidth(160)
        self._progress.setVisible(False)

        wrapper = QWidget()
        row = QHBoxLayout(wrapper)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(NORMAL)
        row.addWidget(bar, stretch=1)
        row.addWidget(self._progress)
        self._toolbar = bar
        self._style_overflow(bar)
        return wrapper

    def _style_overflow(self, bar: QToolBar) -> None:
        """
        Make the toolbar's overflow button impossible to miss.

        Qt shows a 10-pixel "»" when entries do not fit, which read as
        decoration: Open and Save went missing on a narrow window with no
        sign they existed. It becomes a labelled "More" button in the
        highlight colour, and its tooltip names what is hidden.
        """
        # Qt lays the overflow button out in a slot as wide as the style's
        # PM_ToolBarExtensionExtent, about 12 px; a labelled button in that
        # slot is cut off. The toolbar gets a style that asks for more.
        # No base style passed: QProxyStyle takes ownership of a base it is
        # given, and handed the application's own style it freed that style
        # a second time at exit (an access violation after every clean run).
        # Without one it follows the application style and owns nothing.
        self._toolbar_style = _OverflowStyle()
        self._toolbar_style.setParent(bar)
        bar.setStyle(self._toolbar_style)
        self._overflow = bar.findChild(QToolButton, "qt_toolbar_ext_button")
        if self._overflow is None:
            return
        t = theme.tokens()
        self._overflow.setText("More")
        self._overflow.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self._overflow.setStyleSheet(
            f"QToolButton {{ background: {t.signal}; color: {t.on_signal}; "
            f"font-weight: 700; padding: 2px 8px; border: none; }}")
        bar.installEventFilter(self)
        self._update_overflow_hint()

    def _update_overflow_hint(self) -> None:
        if getattr(self, "_overflow", None) is None:
            return
        hidden = hidden_actions(self._toolbar)
        self._overflow.setToolTip(
            "Not enough room for: " + ", ".join(hidden)
            + ". Click to reach them, or widen the window." if hidden
            else "")

    def eventFilter(self, obj, event) -> bool:     # noqa: N802 (Qt API)
        if obj is getattr(self, "_toolbar", None) and \
                event.type() in (QEvent.Resize, QEvent.Show,
                                 QEvent.LayoutRequest):
            QTimer.singleShot(0, self._update_overflow_hint)
        return super().eventFilter(obj, event)

    # ── the palette ─────────────────────────────────────────────

    @property
    def palette_visible(self) -> bool:
        return not self._palette_dock.collapsed

    def set_palette_visible(self, visible: bool) -> None:
        self._palette_dock.set_collapsed(not visible)

    def _on_palette_toggled(self, collapsed: bool) -> None:
        """
        Hand the freed width to the canvas, and take it back on unfold.

        Capping the dock's maximum width is enough to *allow* the canvas to
        grow, but a splitter only reflows on the next resize; setting the sizes
        explicitly makes the change immediate. The width the palette had is
        remembered so unfolding restores it rather than guessing.
        """
        sizes = self._splitter.sizes()
        if len(sizes) == 3 and sum(sizes) > 0:
            if collapsed:
                if sizes[0] > STRIP_WIDTH:
                    self._palette_width = sizes[0]
                give = sizes[0] - STRIP_WIDTH
                self._splitter.setSizes(
                    [STRIP_WIDTH, sizes[1] + give, sizes[2]])
            else:
                # A hidden palette reports 0; it gets back its old width.
                take = max(self._palette_width - sizes[0], 0)
                self._splitter.setSizes(
                    [sizes[0] + take, max(sizes[1] - take, 0), sizes[2]])
        self._palette_action.blockSignals(True)
        self._palette_action.setChecked(not collapsed)
        self._palette_action.blockSignals(False)
        if not self._restoring_palette:
            QSettings(self.SETTINGS_ORG, self.SETTINGS_APP).setValue(
                "sim/palette_collapsed", collapsed)

    def _restore_palette_state(self) -> None:
        stored = QSettings(self.SETTINGS_ORG, self.SETTINGS_APP).value(
            "sim/palette_collapsed", False, type=bool)
        self._restoring_palette = True
        try:
            self._palette_dock.set_collapsed(bool(stored))
        finally:
            self._restoring_palette = False

    # ── scopes ──────────────────────────────────────────────────

    def global_scope_visible(self) -> bool:
        return self._global_button.isChecked()

    def set_global_scope_visible(self, visible: bool) -> None:
        """Show or fold away the global scope, and remember which."""
        self._show_global_scope(visible)
        persist.set_global_scope_open(visible)

    def _show_global_scope(self, visible: bool) -> None:
        self._global_button.blockSignals(True)
        self._global_button.setChecked(visible)
        self._global_button.blockSignals(False)
        self._global_button.setArrowType(
            Qt.DownArrow if visible else Qt.RightArrow)
        self._global_button.setText(
            "Hide global scope" if visible else "Show global scope")
        self._scope.setVisible(visible)
        if visible:
            total = sum(self._centre.sizes())
            if total > 0:
                self._centre.setSizes([total * 3 // 5, total - total * 3 // 5])

    def status_widgets(self) -> tuple[QLabel, QLabel]:
        """The status line and the file name, for the window's status bar."""
        return self._status, self._file_label

    def scope_windows(self) -> dict[str, ScopeWindow]:
        """The open Scope block windows, by block path."""
        return dict(self._scope_windows)

    def open_scope_window(self, key: str) -> ScopeWindow:
        """
        Open (or raise) the window of the Scope block at path ``key``:
        what a double-click on the block does.
        """
        window = self._scope_windows.get(key)
        if window is None:
            model_name = self._canvas.root_model().name
            window = ScopeWindow(key, self._scope_title(key), model_name,
                                 self)
            window.closed.connect(self._forget_scope_window)
            self._scope_windows[key] = window
            window.show_result(self._result, model_name,
                               history=self._scope.history)
        window.show()
        window.raise_()
        window.activateWindow()
        return window

    def _scope_title(self, key: str) -> str:
        """A Scope block's title, read off the level on screen if it is there."""
        block_id = key.rsplit("/", 1)[-1]
        try:
            block = self._canvas.model.block(block_id)
        except ModelError:
            return block_id
        return str(block.params.get("title") or block_id)

    def _forget_scope_window(self, key: str) -> None:
        window = self.sender()
        if self._scope_windows.get(key) is window:
            del self._scope_windows[key]

    def close_scope_windows(self) -> None:
        """Close every Scope block window: another model is on the canvas."""
        windows, self._scope_windows = self._scope_windows, {}
        for window in windows.values():
            window.close()

    # ── the workspace ───────────────────────────────────────────

    @property
    def evaluate(self):
        """What reads ``Kp`` in a block parameter: the console, in the app."""
        return self._canvas.evaluate

    def set_evaluator(self, evaluate) -> None:
        self._canvas.evaluate = evaluate
        self._canvas.validate()

    def bridge(self, show) -> CanvasBridge:
        """The tab as the console's Simulink commands see it."""
        return CanvasBridge(self, show)

    def model_edited(self, model: SimModel) -> None:
        """The console changed ``model``; redraw it if it is the one shown."""
        if model is not self._canvas.root_model():
            return
        if self._canvas.inside_subsystem:
            self._canvas.set_model(model)
        else:
            self._canvas.rebuild()
            self._settings_from_model()

    # ── run settings ────────────────────────────────────────────
    #
    # The stop time, solver and step belong to the model, as in Simulink:
    # they are saved in the .fmdl, and get_param/set_param read and write
    # them. The toolbar shows the model's and writes back to it.

    def _settings_from_model(self) -> None:
        settings = self._canvas.root_model().settings
        self._syncing = True
        try:
            self._t_end.setValue(float(settings.get("StopTime", 10.0)))
            index = self._solver.findText(str(settings.get("Solver", "ode45")))
            if index >= 0:
                self._solver.setCurrentIndex(index)
            self._step.setValue(float(settings.get("MaxStep", 0.0) or 0.0))
        finally:
            self._syncing = False

    def _store_setting(self, name: str, value) -> None:
        if getattr(self, "_syncing", False) or not hasattr(self, "_canvas"):
            return
        self._canvas.root_model().settings[name] = value
        # The run settings are saved with the model, but are not on the
        # undo stack, so the canvas does not report them.
        self._show_unsaved()

    # ── inspector ───────────────────────────────────────────────

    def _on_block_selected(self, item) -> None:
        self._inspector.show_block(item.block if item is not None else None)

    def _apply_params(self, block_id: str, changes: dict) -> None:
        """Route the inspector's edit through the canvas's undo stack."""
        from . import commands as cmd

        self._canvas.undo_stack.push(
            cmd.SetParams(self._canvas, block_id, changes))

    # ── arranging ───────────────────────────────────────────────

    def _align(self, axis: str) -> None:
        self._canvas.align_selection(axis)

    def _distribute(self, axis: str) -> None:
        self._canvas.distribute_selection(axis)

    # ── default model ───────────────────────────────────────────

    def _load_default_model(self) -> None:
        """Start on the course architecture rather than a blank sheet."""
        self._canvas.set_model(course_loop())
        self._canvas.fit_all()
        self._settings_from_model()
        # The starter is not the user's work: nothing to recover yet.
        self.mark_saved()

    # ── running ─────────────────────────────────────────────────

    @guard("Simulation")
    def run_simulation(self) -> None:
        if self._thread is not None:
            return
        # Before anything reads the workspace: they define what it reads.
        self.run_model_scripts(self._canvas.root_model(), BEFORE_RUN)
        problem = self._canvas.validate()
        if problem and "Algebraic loop" not in problem:
            raise CompileError(problem)

        solver = self._solver.currentText()
        step = self._step.value()
        _, is_fixed = resolve_solver(solver)
        if is_fixed and step <= 0:
            raise SimulationError(
                f"{solver} is a fixed-step solver, so it needs an explicit "
                f"step size — set 'Step' to something below your fastest time "
                f"constant.")

        settings = self._canvas.root_model().settings
        options = {
            "t_end": self._t_end.value(),
            "solver": solver,
            "max_step": step if step > 0 else None,
            "rtol": float(settings.get("RelTol", 1e-6)),
            "atol": float(settings.get("AbsTol", 1e-9)),
            "n_points": 2000,
        }

        # The workspace is read here, on the thread that owns it: expressions
        # evaluated, code blocks given their variables. The solver thread
        # gets the compiled copy and never touches the workspace.
        compiled = compile_model(self._canvas.root_model().copy(),
                                 self.evaluate)
        self._worker = _Worker(compiled, options)
        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.failed.connect(self._on_failed)
        self._worker.progress.connect(self._on_progress)

        self._run_btn.setEnabled(False)
        self._stop_btn.setEnabled(True)
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._status.setText("Running…")
        self._thread.start()

    def _on_progress(self, fraction: float) -> None:
        self._progress.setValue(int(fraction * 100))

    def _on_finished(self, result) -> None:
        self._teardown_thread()
        self._result = result
        self._scope.show_result(result)
        model_name = self._canvas.root_model().name
        for window in self._scope_windows.values():
            window.show_result(result, model_name)
        self.simulated.emit(result)
        note = f"Done — {len(result.t)} samples, {result.solver}"
        if result.warnings:
            note += "   ⚠ " + result.warnings[0].splitlines()[0]
        self._status.setText(note)

    def _on_failed(self, message: str) -> None:
        self._teardown_thread()
        if message == "cancelled":
            self._status.setText("Cancelled.")
            return
        self.report_error("Simulation", SimulationError(message))
        self._status.setText("")

    def _cancel(self) -> None:
        if self._worker is not None:
            self._worker.cancelled = True

    def shutdown(self) -> None:
        """Cancel a running simulation and wait for its thread to end."""
        self._cancel()
        self._teardown_thread()

    def _teardown_thread(self) -> None:
        if self._thread is not None:
            self._thread.quit()
            self._thread.wait(2000)
            self._thread = None
        self._worker = None
        self._run_btn.setEnabled(True)
        self._stop_btn.setEnabled(False)
        self._progress.setVisible(False)

    # ── linearise ───────────────────────────────────────────────

    @guard("Linearisation")
    def linearise(self) -> None:
        """
        Linearise the model and hand the result to the analysis tabs.

        Input and output are taken from the selected blocks when two are
        selected, and guessed from the model otherwise.
        """
        model = resolve_model(self._canvas.root_model(), self.evaluate)
        in_port, out_port = self._linearisation_ports(model)
        compiled = compile_model(model, self.evaluate)

        try:
            point = steady_state(compiled)
        except LinearizationError:
            point = None                       # fall back to the initial state

        result = linearize(compiled, in_port, out_port, operating_point=point)
        self.linearised.emit(result.transfer_function(), result.summary())
        self._status.setText(result.summary().replace("\n", "   "))

    def _linearisation_ports(self, model: SimModel) -> tuple[str, str]:
        """
        Decide what to perturb and what to measure.

        If exactly two blocks are selected, the earlier one's input port and
        the later one's output port are used — an explicit choice always wins.
        Otherwise: perturb wherever the first source block drives (so the
        source's own value stays the operating point rather than becoming the
        perturbation), and measure the last block that is neither a source nor
        a sink, which for a control loop is the plant.
        """
        selected = [item.block_id for item in self._canvas.scene().selectedItems()
                    if hasattr(item, "block_id") and hasattr(item, "block")]
        if len(selected) == 2:
            first, second = selected
            in_block, out_block = model.block(first), model.block(second)
            if in_block.inputs and out_block.outputs:
                return (f"{first}.{in_block.inputs[0]}",
                        f"{second}.{out_block.outputs[0]}")

        driven = None
        for block in model:
            if block.category != "Sources" or not block.outputs:
                continue
            wires = model.connections_from(PortRef(block.block_id,
                                                   block.outputs[0]))
            if wires:
                driven = str(wires[0].dst)
                break
        if driven is None:
            raise LinearizationError(
                "could not find an input to perturb. Connect a source block, "
                "or select the input block and the output block (in that "
                "order) and try again.")

        target = None
        for block in model:
            if block.outputs and block.category not in ("Sources", "Sinks"):
                target = f"{block.block_id}.{block.outputs[0]}"
        if target is None:
            raise LinearizationError("could not find an output to measure")
        return driven, target

    # ── files ───────────────────────────────────────────────────

    @guard("Open model")
    def open_model(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open model", "",
            "Evans models (*.evx *.fmdl);;All files (*)")
        if path and self.settle_unsaved():
            self.load_model(path)

    @guard("Open model")
    def load_model(self, path: str | Path, remember: bool = True) -> None:
        """
        Open a model file onto the canvas.

        ``remember`` puts it on the recent-files list; an example opened
        from the menu is not a file of the user's, so it stays off.
        """
        model = SimModel.load(path)
        # As PreLoadFcn does: before the canvas checks the parameters.
        self.run_model_scripts(model, ON_OPEN)
        self._canvas.set_model(model)
        self._canvas.fit_all()
        self._scope.clear()
        self._result = None
        self._status.setText(f"Loaded {path}")
        if remember:
            # An example's file is inside Evans: Save asks where instead.
            self._path = Path(path)
        self.mark_saved()
        if remember:
            self.file_used.emit(Path(path))

    # ── model scripts ───────────────────────────────────────────
    #
    # A model's .m files, run in the console's workspace on open and before
    # each run (see sim/scripts.py). The console is the one runner, so their
    # output and errors land where everything else's do.

    def set_script_console(self, console, search=list) -> None:
        """``console`` runs scripts (``run_model_script``, ``note``);
        ``search()`` lists the folders a bare script name is looked for in."""
        self._script_console = console
        self._script_search = search

    @staticmethod
    def _is_trusted(path) -> bool:
        """A model built here, an example, or a file on the trusted list."""
        if path is None:
            return True
        from ...examples import FOLDER
        if Path(path).resolve().parent == FOLDER:
            return True
        return path_key(path) in set(persist.trusted_models())

    def scripts_allowed(self, model: SimModel, when: str) -> bool:
        """
        Whether ``model``'s scripts due ``when`` may run: yes for a trusted
        model, else whatever the user answers (asked once a session).
        """
        if self._is_trusted(model.path) or not needs_trust(
                model.scripts, when, model.path, []):
            return True
        key = path_key(model.path)
        if key in self._allowed_once:
            return True
        answer = self._ask_trust(model, when)
        if answer == "trust":
            persist.trust_model(model.path)
        elif answer == "run":
            self._allowed_once.add(key)
        return answer in ("trust", "run")

    def _ask_trust(self, model: SimModel, when: str) -> str:
        """``"run"`` (this session), ``"trust"`` (from now on) or ``"skip"``."""
        names = ", ".join(s.name for s in due(model.scripts, when))
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle("Run the model's scripts?")
        box.setText(f"{Path(model.path).name} runs MATLAB code "
                    f"{WHEN_TEXT[when]}: {names}.")
        box.setInformativeText(
            "A script can do anything your account can: read and write "
            "files, run programs. Run it only if you trust where this model "
            "came from.")
        run = box.addButton("Run this time", QMessageBox.AcceptRole)
        trust = box.addButton("Trust this model", QMessageBox.YesRole)
        skip = box.addButton("Don't run", QMessageBox.RejectRole)
        box.setDefaultButton(skip)
        box.setEscapeButton(skip)
        box.exec()
        clicked = box.clickedButton()
        if clicked is run:
            return "run"
        return "trust" if clicked is trust else "skip"

    def run_model_scripts(self, model: SimModel, when: str) -> int:
        """
        Run ``model``'s scripts due ``when``; returns how many ran.

        Before a run, a missing, failing or refused script raises
        :class:`ScriptError`, which stops the run. On open, the model opens
        whatever happens and the console says what did.
        """
        scripts = due(model.scripts, when)
        if not scripts:
            return 0
        console = self._script_console
        if console is None:
            if when == BEFORE_RUN:
                raise ScriptError(scripts[0].name,
                                  "there is no console to run it in")
            return 0
        if not self.scripts_allowed(model, when):
            if when == BEFORE_RUN:
                raise ScriptError(
                    scripts[0].name,
                    "not run, since this model is not trusted, so the run "
                    "stopped; Scripts… runs it, or trust the model to")
            console.note(f"{model.name}: its scripts on open did not run "
                         f"(the model is not trusted). Scripts… runs them.")
            return 0

        def warn(text: str) -> None:
            console.note(text)
            self._status.setText(text)

        return run_scripts(
            model.scripts, when,
            lambda path, _script: console.run_model_script(
                path, WHEN_TEXT[when]),
            model_path=model.path, search=self._script_search(), warn=warn)

    @guard("Model scripts")
    def edit_model_scripts(self) -> None:
        """The Model scripts dialog, for the model on the canvas."""
        from .scripts_dialog import ModelScriptsDialog

        model = self._canvas.root_model()
        dialog = ModelScriptsDialog(model, self, run_now=self.run_scripts_now,
                                    search=self._script_search)
        if dialog.exec():
            model.scripts = dialog.scripts()
            self._show_unsaved()

    @guard("Model scripts")
    def run_scripts_now(self, scripts) -> int:
        """
        The dialog's Run now: the scripts given, in order, whatever they are
        ticked for. Asked for by name, so there is no trust prompt; a failing
        one stops the rest.
        """
        from ...sim.scripts import ModelScript

        if not scripts:
            return 0
        console = self._script_console
        if console is None:
            raise ScriptError(scripts[0].name,
                              "there is no console to run it in")
        model = self._canvas.root_model()
        chosen = [ModelScript(s.path, before_run=True) for s in scripts]
        count = run_scripts(
            chosen, BEFORE_RUN,
            lambda path, _s: console.run_model_script(path, "run now"),
            model_path=model.path, search=self._script_search())
        self._canvas.validate()
        return count

    # ── export ──────────────────────────────────────────────────

    @guard("Export diagram")
    def export_diagram(self, path: str | Path | None = None) -> None:
        """The diagram on screen as SVG, PDF or PNG."""
        if path is None:
            path, _ = QFileDialog.getSaveFileName(
                self, "Export diagram",
                f"{self._canvas.root_model().name}.svg",
                "SVG (*.svg);;PDF (*.pdf);;PNG (*.png)")
            if not path:
                return
        self._canvas.export_image(path)
        self._status.setText(f"Exported the diagram to {path}")

    @guard("Print diagram")
    def print_diagram(self) -> None:
        self._canvas.print_diagram()

    @guard("Export data")
    def export_data(self, path: str | Path | None = None) -> None:
        """The last run's signals as CSV or .mat."""
        if self._result is None:
            raise SimulationError("Run the model first: there is no data "
                                  "to export yet.")
        if path is None:
            path, _ = QFileDialog.getSaveFileName(
                self, "Export signals",
                f"{self._canvas.root_model().name}.csv",
                "CSV (*.csv);;MATLAB data (*.mat)")
            if not path:
                return
        self._scope.export(path)
        self._status.setText(f"Exported the signals to {path}")

    @property
    def model_path(self) -> Path | None:
        """The file the model on the canvas is saved to, if it has one."""
        return self._path

    def _forget_path(self) -> None:
        self._path = None
        self._format_asked = False
        self._show_unsaved()

    @guard("Save model")
    def save_model(self) -> None:
        """
        Save to the model's own file, or ask where when it has none.

        The first Save of a ``.fmdl`` offers the new ``.evx`` once. Yes
        writes ``name.evx`` beside it and carries on from there; the old
        file is left exactly as it was. An ``.evx`` is never asked about.
        """
        path = self._path
        if path is None:
            self.save_model_as()
            return
        if path.suffix.lower() == LEGACY_SUFFIX and not self._format_asked:
            self._format_asked = True
            if self.ask_new_format():
                path = path.with_suffix(SUFFIX)
                if path.exists():
                    # Someone's .evx is already there: let them choose.
                    self.save_model_as(path)
                    return
        self._write_model(path)

    @guard("Save model")
    def save_model_as(self, start: Path | None = None) -> None:
        """Save to a file the user picks: ``.evx``, or ``.fmdl`` for an
        older Evans."""
        if not isinstance(start, Path):            # a toolbar click's bool
            folder = self._path.parent if self._path is not None else None
            name = f"{self._canvas.root_model().name}{SUFFIX}"
            start = folder / name if folder is not None else Path(name)
        new_filter = f"Evans model (*{SUFFIX})"
        old_filter = f"Older Evans model (*{LEGACY_SUFFIX})"
        path, chosen = QFileDialog.getSaveFileName(
            self, "Save model", str(start), f"{new_filter};;{old_filter}")
        if not path:
            return
        path = Path(path)
        if path.suffix.lower() not in (SUFFIX, LEGACY_SUFFIX):
            path = path.with_name(path.name + (
                LEGACY_SUFFIX if chosen == old_filter else SUFFIX))
        if path.suffix.lower() == LEGACY_SUFFIX:
            # Chosen on purpose, for an older Evans: Save does not ask again.
            self._format_asked = True
        self._write_model(path)

    def ask_new_format(self) -> bool:
        """The one-time question on a ``.fmdl``: True to save as ``.evx``."""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle("Save model")
        box.setText("Evans is moving to a new model file, .evx. "
                    "Save this one in the new format?")
        box.setInformativeText(
            f"Evans writes {self._path.with_suffix(SUFFIX).name} beside "
            f"{self._path.name} and leaves the old file as it is. Older "
            "versions of Evans cannot open .evx files.")
        new = box.addButton(f"Save as {SUFFIX}", QMessageBox.AcceptRole)
        keep = box.addButton(f"Keep {LEGACY_SUFFIX} this time",
                             QMessageBox.RejectRole)
        box.setDefaultButton(new)
        box.setEscapeButton(keep)
        box.exec()
        return box.clickedButton() is new

    def _write_model(self, path: Path) -> None:
        model = self._canvas.root_model()
        # The user's own model stays trusted under its new name; one opened
        # from someone else's file does not become trusted by a Save.
        own = self._is_trusted(model.path)
        # Written in full before the canvas takes the new file as its own.
        model.save(path)
        if own:
            persist.trust_model(path)
        self._path = path
        self._status.setText(f"Saved {path}")
        self.mark_saved()
        self.file_used.emit(path)

    # ── crash recovery ──────────────────────────────────────────

    def _model_text(self) -> str:
        return json.dumps(self._canvas.root_model().to_dict(), indent=1,
                          sort_keys=True)

    def mark_saved(self) -> None:
        """The diagram on screen is the one its file holds."""
        self._saved_state = self._model_text()
        self._show_unsaved()

    # ── unsaved changes ─────────────────────────────────────────
    #
    # Unsaved means the diagram differs from its baseline (`mark_saved`):
    # the starter and an example opened unchanged are not. A run does not
    # touch the model (the solver gets a compiled copy, the result lives
    # on the tab), so running never makes it unsaved.

    def is_unsaved(self) -> bool:
        """Whether the diagram differs from its file (or has none to match)."""
        return self._model_text() != self._saved_state

    def _show_unsaved(self) -> None:
        """The file label: the model's file name, marked when unsaved."""
        if not hasattr(self, "_format_asked"):     # still building
            return
        path = self._path
        if path is not None:
            name = path.name
        else:
            name = self._canvas.root_model().name or "untitled"
        self._file_label.setText(marked(name, self.is_unsaved()))
        self._file_label.setToolTip(
            str(path) if path is not None else "Not saved to a file yet")

    def _ask_to_save(self) -> str:
        """'save', 'discard' or 'cancel'. A method so tests can answer it."""
        return ask_to_save(
            self, "Save model?",
            f"The model {self._canvas.root_model().name} has changes "
            "that are not saved.")

    def settle_unsaved(self) -> bool:
        """
        Before the diagram is replaced or Evans quits: save, discard or
        cancel its changes. True unless the user cancelled, which includes
        cancelling Save's file dialog. Nothing unsaved asks nothing.
        """
        if not self.is_unsaved():
            return True
        choice = self._ask_to_save()
        if choice == "cancel":
            return False
        if choice == "save":
            self.save_model()
            return not self.is_unsaved()
        return True

    def recovery_items(self) -> list:
        """The diagram, when it differs from its file, for recovery."""
        from ..recovery import MODEL, Item
        text = self._model_text()
        if text == self._saved_state:
            return []
        return [Item(MODEL, "model", self._canvas.root_model().name, text)]

    def restore_model_text(self, text: str) -> None:
        """A recovered diagram on the canvas, unsaved."""
        self._canvas.set_model(SimModel.from_dict(json.loads(text)))
        self._canvas.fit_all()
        self._scope.clear()
        self._result = None
        self._saved_state = None
        self._show_unsaved()
        self._status.setText("Restored a recovered model; save it to keep it.")

    # ── misc ────────────────────────────────────────────────────

    def _on_path_changed(self, crumbs: list) -> None:
        inside = len(crumbs) > 1
        self._up_action.setVisible(inside)
        self._crumb.setText(" ▸ ".join(crumbs) if inside else "")

    def _on_model_changed(self) -> None:
        self._show_unsaved()
        problem = self._canvas.validate()
        if problem:
            self._status.setText(problem.splitlines()[0])

    def refresh(self, arch=None) -> None:
        """Called when the tab is shown; nothing to recompute."""


class CanvasBridge:
    """
    The Model tab, as ``open_system``, ``set_param`` and ``sim`` see it.

    The console's Simulink commands look a model name up here first, so the
    model on screen is the one they read and edit; ``show`` puts a model on
    the canvas, and ``changed`` redraws after the console has edited it.
    """

    def __init__(self, tab: SimTab, show) -> None:
        self._tab = tab
        self._show = show

    def model(self) -> SimModel:
        return self._tab._canvas.root_model()

    def show(self, model: SimModel) -> None:
        self._show(model)

    def changed(self, model: SimModel) -> None:
        self._tab.model_edited(model)

    def scripts_allowed(self, model: SimModel, when: str) -> bool:
        """The Model tab's trust check, so the console asks the same way."""
        return self._tab.scripts_allowed(model, when)


# ──────────────────────────────────────────────────────────────
#  Starter model
# ──────────────────────────────────────────────────────────────

def course_loop() -> SimModel:
    """
    The ch.5 architecture, laid out left to right.

    Opening on a working loop rather than an empty canvas means the first
    thing anyone does is press Run and see a step response.

    No Scope block. Every signal a run produces is logged and can be picked
    in the scope pane below the canvas, so a Scope block here only duplicated
    that pane — and wired to ``K2``, it drew the controller effort that the
    pane's own default (``r`` and ``G``) deliberately leaves out. The block
    type stays in the palette for models that want a named view.
    """
    m = SimModel("course loop")
    # 220 px between centres: a block is 110 wide, so every wire has 110 px
    # of its own and the feedback path a clear run underneath.
    m.add("Step", "r", x=-330, y=0, step_time=0.0)
    m.add("Sum", "e", x=-110, y=0, signs="+-")
    m.add("PID", "K2", x=110, y=0, Kp=2.0, Ki=1.0)
    m.add("TransferFcn", "G", x=330, y=0, num="1", den="1, 1, 0")

    m.connect("r", "e.in1")
    m.connect("e", "K2")
    m.connect("K2", "G")
    m.connect("G", "e.in2")
    return m
