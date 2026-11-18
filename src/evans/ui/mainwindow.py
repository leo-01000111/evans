r"""
Main application window.
========================

::

  ┌──────────────────────────────────────────────────────────┐
  │ ▣ File Export View …              Evans — …          ─ □ ✕ │  title bar
  ├──────────────────────────────────────────────────────────┤
  │ G(s) = …   K₂(s) = …   ● stable   PM 60°   [Edit loop]   │  context bar
  ├──────────────────────────────────────────────────────────┤
  │ 📌 Snapshot  [ … ]  Restore  Delete  Compare   (hideable)│
  ├──────────────────────────────────────────────────────────┤
  │ System │ Time │ Frequency │ … │ Simulink │ Modern        │
  │                                                          │
  │                    the analysis area                     │
  └──────────────────────────────────────────────────────────┘

Each workspace page is ``[content | side panel]`` (:mod:`.side_panel`), the
panel opened and closed with View ▸ Side panel (Ctrl+\). On Analyse its
*Loop* tab holds the architecture diagram and the block editor, which used
to occupy 420–760 px on every tab and then a dock left of the rail; what is
always visible instead is the context bar, which answers "what is loaded and
is it stable?" in one strip. Cedric is the last tab of every panel: one
assistant panel, moved into the workspace in view.

Geometry, each side panel (open, tab, width) and the current workspace are
saved on close and restored on launch; View ▸ Reset layout puts them back to
the defaults.

The title bar (:mod:`.titlebar`) carries the menus. On Windows it replaces
the native caption while keeping the native frame (:mod:`.winframe`), so the
window still snaps, resizes and casts its shadow; View ▸ Integrated title bar
turns that off, and everywhere else the caption is the system's own.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import control as ctl
from PySide6.QtCore import QProcess, QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QUndoGroup, QUndoStack
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMenuBar,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..console.apps import AppRequest, set_app_sink
from ..core.architecture import CourseArchitecture
from ..core.collection import SnapshotStore, SystemCollection
from ..core.report import text_report
from ..core.session import load_session_dict, session_dict
from ..core.tf_utils import (
    first_order,
    second_order,
    unity,
)
from ..sim.model import is_model_file, preferred_file
from . import help, iconset, keys, persist, recovery, theme, winframe
from .apps import SnapshotBar
from .assistant import AssistantPanel, LoopSource, ModelSource
from .block_editor import BlockEditor
from .console import ConsolePanel, FigureArea
from .context_bar import ContextBar
from .design import TIGHT
from .design_panel import DesignPanel
from .diagram.fixed_diagram import FixedDiagramView
from .loop_undo import ReplaceLoop
from .panes import DEFAULT_LAYOUT, LAYOUTS, PANE_KINDS, PaneGrid, Source
from .persist import RecentFiles
from .side_panel import SidePanel, page_with_panel
from .sim.sim_tab import SimTab
from .tabs.modern import ModernTab
from .titlebar import TitleBar
from .updater import Updater
from .workspace import Workspace, WorkspaceStack


class MainWindow(QMainWindow):

    APP_TITLE = "Evans — Classical & Modern Control"

    def __init__(self, arch: CourseArchitecture | None = None) -> None:
        super().__init__()
        self._arch = arch or CourseArchitecture(
            G  = first_order(1.0, 1.0),
            K2 = unity(),
            K1 = unity(),
            H  = unity(),
        )
        self.setWindowTitle(self.APP_TITLE)
        self.resize(1400, 850)
        #: Undo for the loop (G, K1, K2, H); the Model workspace keeps the
        #: canvas's own stack. `_loop_baseline` is the loop as last seen, so a
        #: change made by a widget that writes the architecture directly can
        #: still be recorded with the state it started from.
        self._loop_undo = QUndoStack(self)
        self._loop_undo.setUndoLimit(200)
        self._loop_baseline = session_dict(self._arch)
        self._undo_seen: dict = {}
        #: Snapshots are shared: the bar above the tabs, the Compare button
        #: and the console all read the same store.
        self.snapshots = SnapshotStore()
        #: Scripts and models opened or saved, for File ▸ Open recent.
        self.recent_files = RecentFiles()
        #: Unsaved scripts were settled for quitting; see `confirm_quit`.
        self._quit_confirmed = False
        # Before the menus: the title bar holds the menu bar they fill.
        self._title_bar = TitleBar(self)
        #: Help ▸ Check for updates; before the menus, which call it.
        self.updater = Updater(self)
        # Looked up at click time, not bound now, so the tests can patch them.
        self._title_bar.minimize_requested.connect(lambda: self.showMinimized())
        self._title_bar.maximize_requested.connect(
            lambda: self.toggle_maximized())
        self._title_bar.close_requested.connect(lambda: self.close())
        self.setMenuWidget(self._title_bar)
        self._native_frame = winframe.NativeFrame(self, self._title_bar)
        self._build_ui()
        self._build_menus()
        self._build_status_bar()
        self.updater.status.connect(self._status.showMessage)
        self.set_integrated_title_bar(
            persist.integrated_title_bar(default=winframe.supported()),
            remember=False)
        set_app_sink(self.open_app)

    # ── Title bar ─────────────────────────────────────────────

    def menuBar(self) -> QMenuBar:          # noqa: N802 (Qt API)
        """
        The menu bar inside the title bar.

        ``QMainWindow.menuBar()`` would make a new, empty one and put it in
        place of the title bar, since the menu widget is not a QMenuBar.
        """
        return self._title_bar.menu_bar

    @property
    def title_bar(self) -> TitleBar:
        return self._title_bar

    @property
    def integrated_title_bar(self) -> bool:
        """Whether the native caption is gone and our strip replaces it."""
        return self._title_bar.chrome_visible

    def toggle_maximized(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def set_integrated_title_bar(self, on: bool, *, remember: bool = True
                                 ) -> bool:
        """
        Menus and window buttons in one strip, or the system's caption.

        Only on Windows; elsewhere, or if Windows refuses, the caption stays
        and the strip is a plain menu bar. ``remember`` keeps the choice for
        the next launch. Returns whether the strip is now integrated.
        """
        if remember:
            persist.set_integrated_title_bar(on)
        active = False
        if on:
            self._title_bar.set_chrome_visible(True)
            active = self._native_frame.install()
        if not active:
            self._native_frame.uninstall()
            self._title_bar.set_chrome_visible(False)
        action = getattr(self, "_act_title_bar", None)
        if action is not None:
            action.blockSignals(True)
            action.setChecked(on)
            action.blockSignals(False)
        return active

    def nativeEvent(self, event_type, message):   # noqa: N802 (Qt API)
        frame = getattr(self, "_native_frame", None)
        if frame is not None and frame.enabled:
            try:
                handled, result = frame.handle(int(message))
            except Exception:                       # noqa: BLE001
                # Never take the window down with us: stop handling at once,
                # and put the system caption back once this message is done.
                frame.enabled = False
                QTimer.singleShot(0, self._native_frame_failed)
                return False, 0
            if handled:
                return True, result
        return super().nativeEvent(event_type, message)

    def _native_frame_failed(self) -> None:
        self._native_frame.uninstall()
        self._title_bar.set_chrome_visible(False)
        self._status.showMessage(
            "The integrated title bar failed; using the system's instead",
            8000)

    # ── UI construction ───────────────────────────────────────

    def _build_ui(self) -> None:
        self._stack = WorkspaceStack()
        self.setCentralWidget(self._stack)
        self._stack.changed.connect(self._on_workspace_changed)
        self._stack.rail.help_requested.connect(help.open_help)
        self._stack.rail.cedric_requested.connect(
            lambda: self.set_cedric_visible(True))

        self._stack.add_page(Workspace.ANALYSE, self._build_analyse())
        # The Simulink tab becomes the Model workspace outright: it is a
        # different model with its own undo stack and file format, not another
        # view of the architecture the other panels share.
        self._sim_tab = SimTab()
        self._sim_tab._canvas.path_changed.connect(
            lambda _path: self._sync_undo_group())
        self._stack.add_page(Workspace.MODEL, self._sim_tab)
        self._stack.add_page(Workspace.CONSOLE, self._build_console())
        #: Each workspace's side panel; Cedric is the last tab of each.
        self._side_panels: dict[Workspace, SidePanel] = {
            Workspace.ANALYSE: self._analyse_side,
            Workspace.MODEL: self._sim_tab.side_panel,
            Workspace.CONSOLE: self._console_side,
        }
        self._build_cedric()

        # ── Connections ──
        self._diagram.block_selected.connect(self._on_block_selected)
        self._diagram.signal_selected.connect(self._on_signal_selected)
        self._diagram.architecture_changed.connect(self._on_arch_changed)
        self._editor.tf_changed.connect(self._on_tf_edited)
        self._sim_tab.linearised.connect(self._on_linearised)
        self._sim_tab.file_used.connect(self.recent_files.add)
        self._console.editor.file_used.connect(self.recent_files.add)
        # Files dropped on the window open where they belong; the canvas
        # keeps block drops for itself and hands file drops up.
        self.setAcceptDrops(True)
        self._sim_tab.files_dropped.connect(self.open_files)

    def _build_analyse(self) -> QWidget:
        central = QWidget()
        main_lay = QVBoxLayout(central)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(TIGHT)

        # ── the model context bar ──
        #
        # What used to be a permanent 420–760 px column is now one strip. The
        # diagram and the block editor are the side panel's Loop tab, opened
        # on demand (Ctrl+\), so the analysis area gets the width instead of
        # a picture of an architecture most panes do not need.
        self._context = ContextBar(self._arch)
        self._context.edit_requested.connect(self.show_loop_editor)
        main_lay.addWidget(self._context)

        # ── the snapshot bar ──
        #
        # Above the tabs because a snapshot is of the whole architecture, not
        # of whatever panel happens to be open — taking one on the Frequency
        # tab and restoring it on the Time tab is the point.
        self._snapshot_bar = SnapshotBar(self._arch, self.snapshots)
        self._snapshot_bar.restored.connect(self._on_snapshot_restored)
        self._snapshot_bar.compare_requested.connect(self._compare_snapshots)
        self._snapshot_bar.setVisible(persist.snapshot_bar())
        main_lay.addWidget(self._snapshot_bar)

        # The pane grid *is* the analysis area. It used to sit beside a
        # second "Tabs" view of the same widgets; every workflow that view
        # held (System, Time, Frequency, ...) is now a pane kind, so nothing
        # is reachable only from a tab bar, and tuning stays a matter of
        # watching several views move together.
        self._grid = PaneGrid(self._arch, tab_factory=self._make_tab)
        # Every plot pane's Compare menu lists the snapshots.
        self._grid.snapshots = self.snapshots
        main_lay.addWidget(self._wrap_grid(), stretch=1)
        self._sync_layout_buttons()

        # ── the side panel: Loop · Design · Cedric, closed by default ──
        side = SidePanel("analyse")
        loop = side.add_tab("loop", "Loop")
        # The diagram is inherently wide and short (roughly 3.3:1), so cap its
        # height and give the space it cannot use to the block editor.
        self._diagram = FixedDiagramView(self._arch)
        self._diagram.setMinimumHeight(150)
        self._diagram.setMaximumHeight(260)
        loop.layout().addWidget(self._diagram, stretch=0)
        self._editor = BlockEditor()
        loop.layout().addWidget(self._editor, stretch=1)
        # Gain · Compensator · PID; what the three docked apps were.
        self._design = DesignPanel(self._arch, self._apply_design)
        side.add_tab("design", "Design", self._design)
        side.set_open(False)
        self._analyse_side = side
        return page_with_panel(central, side)


    def _wrap_grid(self) -> QWidget:
        """
        The pane grid, its layout selector at the right of the top-right
        pane's header rather than on a row of its own.
        """
        selector = QWidget()
        row = QHBoxLayout(selector)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(TIGHT)
        self._layout_buttons = {}
        # Pictograms, not "Panes: 1  1 × 2  2 × 2": a pane's header has the
        # width of one pane, which with the apps docked is not much.
        for count, label, name in ((1, "1", "grid-1"), (2, "1 × 2", "grid-1x2"),
                                   (4, "2 × 2", "grid-2x2")):
            button = QToolButton()
            button.setText(label)
            iconset.bind(button, name)
            button.setToolButtonStyle(Qt.ToolButtonIconOnly)
            button.setCheckable(True)
            button.setAutoRaise(True)
            button.setToolTip(f"{label}: show {count} analysis pane"
                              f"{'s' if count > 1 else ''}")
            button.setAccessibleName(f"{count} panes")
            button.clicked.connect(
                lambda _checked=False, n=count: self.set_pane_layout(n))
            row.addWidget(button)
            self._layout_buttons[count] = button
        self._grid.set_corner(selector)
        return self._grid

    def set_snapshot_bar_visible(self, on: bool) -> None:
        """Settings ▸ Show snapshot bar, remembered for the next launch."""
        persist.set_snapshot_bar(on)
        self._snapshot_bar.setVisible(on)
        self._act_snapshots.setChecked(on)

    def set_pane_layout(self, count: int) -> None:
        """1, 2 or 4 panes. A fresh 2×2 opens on step, Bode, locus, metrics."""
        keys = None if self._grid.count else DEFAULT_LAYOUT
        self._grid.set_layout_size(count, keys)
        self._sync_layout_buttons()
        self._status.showMessage(
            f"{count} analysis pane{'s' if count > 1 else ''}", 3000)

    def _sync_layout_buttons(self) -> None:
        for size, button in self._layout_buttons.items():
            button.blockSignals(True)
            button.setChecked(size == self._grid.count)
            button.blockSignals(False)

    def _make_tab(self, name: str, arch):
        """
        Which widget a pane gets when it asks for a whole workflow.

        Each pane owns its own instance (a widget lives in one place), so the
        signals that used to be wired once, at construction, are wired here,
        once per instance the grid creates.
        """
        from .tabs.design_tab import DesignTab
        from .tabs.frequency_tab import FrequencyTab
        from .tabs.performance_tab import PerformanceTab
        from .tabs.stability_tab import StabilityTab
        from .tabs.system_tab import SystemTab
        from .tabs.time_tab import TimeTab

        factory = {"system": SystemTab, "time": TimeTab,
                   "frequency": FrequencyTab, "stability": StabilityTab,
                   "performance": PerformanceTab, "design": DesignTab,
                   "modern": ModernTab}.get(name)
        if factory is None:
            return None
        widget = factory(arch)
        if name == "design":
            widget.controller_changed.connect(self._on_controller_designed)
        elif name == "modern":
            widget.ctx.status.connect(
                lambda m: self._status.showMessage(m, 6000))
            widget.model_sent_to_analysis.connect(
                self._on_modern_model_sent)
        return widget

    def _build_console(self) -> QWidget:
        """
        The Console workspace: transcript and variables over the figures.

        The console used to be a dock hidden by default, which made a
        first-class way of driving this application into a panel you had to
        know existed. Plot commands drew into a second hidden dock.
        """
        self._figures = FigureArea()
        self._console = ConsolePanel(self._figures,
                                     extra=self._console_state())
        self._sim_tab.set_evaluator(self._console.interpreter.evaluate)
        runtime = self._console.interpreter._matlab_runtime
        self._sim_tab.set_script_console(
            self._console.console,
            lambda: [runtime().folder, *runtime().path])
        self._console.interpreter.simulink = self._sim_tab.bridge(
            lambda model: self._on_console_model(model.name, model))
        self._sim_tab.simulated.connect(self._on_simulated)
        self._console.open_system.connect(self._on_console_system)
        self._console.console.executed.connect(self._on_console_executed)
        self._console.open_model.connect(self._on_console_model)
        help.set_console(self._run_from_help, lambda: self._console.running)
        # A figure drawn from anywhere pulls the workspace into view, so
        # `step(G)` typed on the Analyse page does not draw somewhere unseen.
        # Not for a model's setup script: that runs in the background of the
        # Model page, and its figures wait on the Console page.
        self._figures.figure_added.connect(self._reveal_figures)

        split = QSplitter(Qt.Vertical)
        split.addWidget(self._console)
        split.addWidget(self._figures)
        # Hidden on the Live tab: its figures are inline under their cells,
        # and a strip of the same figures below them only takes room.
        self._console.figure_area_wanted.connect(self._figures.setVisible)
        split.setStretchFactor(0, 3)
        split.setStretchFactor(1, 2)
        # The workspace and history beside every Console tab, not only the
        # first: the side panel is outside the console's own tabs.
        side = SidePanel("console")
        side.add_tab("workspace", "Workspace", self._console.workspace)
        side.add_tab("history", "History", self._console.history)
        self._console.side_requested.connect(self._show_console_side)
        self._console_side = side
        return page_with_panel(split, side)

    def _show_console_side(self, key: str) -> None:
        self._console_side.set_current(key)
        self._console_side.set_open(True)
        self._sync_side_action()

    def _reveal_figures(self) -> None:
        if not self._console.console.in_model_script:
            self._stack.set_current(Workspace.CONSOLE)

    # ── Side panels and Cedric ────────────────────────────────

    def _build_cedric(self) -> None:
        """
        Cedric, the assistant: one panel, the last tab of every workspace's
        side panel. It is moved into the workspace in view
        (`_place_cedric`), so the conversation is the same object wherever
        it is read.
        """
        self._cedric_panel = AssistantPanel()
        self._loop_source = LoopSource(lambda: self._arch,
                                       lambda: self._context.describe())
        self._model_source = ModelSource(
            lambda: self._sim_tab._canvas.root_model())
        for workspace, side in self._side_panels.items():
            side.add_tab("cedric", "Cedric")
            side.toggled.connect(
                lambda _on, w=workspace: self._on_side_changed(w))
            side.tab_changed.connect(
                lambda _key, w=workspace: self._on_side_changed(w))
        panel = self._cedric_panel
        panel.run_command.connect(self._console.execute)
        panel.paste_command.connect(self._console.recall)
        self._console.cedric_requested.connect(self._ask_cedric)
        self._place_cedric(self._stack.current)

    def _place_cedric(self, workspace) -> None:
        """Move Cedric into ``workspace``'s panel; read what it shows."""
        if getattr(self, "_cedric_panel", None) is None:
            return                                  # still being built
        holder = self._side_panels[workspace].holder("cedric")
        if self._cedric_panel.parentWidget() is not holder:
            holder.layout().addWidget(self._cedric_panel)
        self._cedric_panel.set_source({
            Workspace.ANALYSE: self._loop_source,
            Workspace.MODEL: self._model_source,
            Workspace.CONSOLE: self._console.assistant_source,
        }[workspace])

    @property
    def side_panel(self) -> SidePanel:
        """The side panel of the workspace in view."""
        return self._side_panels[self._stack.current]

    def side_panel_of(self, workspace) -> SidePanel:
        return self._side_panels[workspace]

    def set_side_panel_open(self, on: bool) -> None:
        """Open or close the side panel of the workspace in view."""
        self.side_panel.set_open(on)
        self._sync_side_action()

    def toggle_side_panel(self, *_ignored) -> None:
        """View ▸ Side panel (Ctrl+backslash): the current workspace's."""
        self.set_side_panel_open(not self.side_panel.is_open)

    def show_loop_editor(self, *_ignored) -> None:
        """*Edit loop*: the Analyse panel, open on Loop."""
        side = self._side_panels[Workspace.ANALYSE]
        if self._stack.current is not Workspace.ANALYSE:
            self._stack.set_current(Workspace.ANALYSE)
        side.set_current("loop")
        side.set_open(True)
        self._sync_side_action()

    def _ask_cedric(self, context, source, action: str) -> None:
        """
        *Ask Cedric* on a console selection or error: his context is on the
        Console, so go there, open him and pass it on.
        """
        if self._stack.current is not Workspace.CONSOLE:
            self._stack.set_current(Workspace.CONSOLE)
        self.set_cedric_visible(True)
        self._cedric_panel.request(context, source, action)

    def set_cedric_visible(self, wanted: bool) -> None:
        """
        Open the current workspace's side panel on Cedric, or close it if
        it is showing him. Stays on the workspace in view.
        """
        side = self.side_panel
        if wanted:
            side.set_current("cedric")
            side.set_open(True)
        elif side.is_open and side.current == "cedric":
            side.set_open(False)
        self._sync_side_action()

    @property
    def cedric_showing(self) -> bool:
        """Whether Cedric is the open tab of the current side panel."""
        side = self.side_panel
        return side.is_open and side.current == "cedric"

    def _on_side_changed(self, workspace) -> None:
        if workspace is self._stack.current:
            self._sync_side_action()

    def _sync_side_action(self) -> None:
        """The View menu's check marks follow the panel in view."""
        if getattr(self, "_side_panels", None) is None:
            return
        for name, checked in (("_act_side", self.side_panel.is_open),
                              ("_act_cedric", self.cedric_showing)):
            action = getattr(self, name, None)
            if action is not None:
                action.blockSignals(True)
                action.setChecked(checked)
                action.blockSignals(False)

    def _console_state(self) -> dict:
        """
        What the console starts with from the app.

        ``arch`` and ``model`` are live references, so a command typed at the
        prompt and a change made in a tab act on the same objects rather than
        on copies that quietly diverge.
        """
        return {
            "arch": self._arch,
            "G": self._arch.block_tf("G"),
            "K2": self._arch.block_tf("K2"),
            "model": self._sim_tab._canvas.model,
        }

    def _on_console_system(self, name: str, system) -> None:
        """A system was double-clicked in the workspace: analyse it as G(s)."""
        tf = ctl.ss2tf(system) if hasattr(system, "A") else system
        self.change_loop(f"Load {name} as G",
                         lambda: self._arch.set_block("G", tf))
        self._stack.set_current(Workspace.ANALYSE)
        self._status.showMessage(f"{name} loaded as G(s)", 6000)

    def _on_simulated(self, result) -> None:
        """A run on the Model tab: its output goes to the workspace as out."""
        from ..console import matlab_runtime  # noqa: F401  (imports lib_sim)
        from ..console.lib_sim import simulation_output
        self._console.interpreter.namespace["out"] = simulation_output(result)
        self._console.workspace.refresh()

    def _on_console_model(self, name: str, model) -> None:
        """A Simulink model was double-clicked: open it on the canvas."""
        replacing = model is not self._sim_tab._canvas.root_model()
        if replacing and not self._settle_model():
            return
        self._sim_tab._canvas.set_model(model)
        self._sim_tab._canvas.fit_all()
        self._stack.set_current(Workspace.MODEL)
        self._status.showMessage(f"{name} opened on the canvas", 6000)

    # ── Layout ───────────────────────────────────────────────

    #: Where `QSettings` keeps this window's layout.
    SETTINGS_ORG = "Evans"
    SETTINGS_APP = "Evans"

    def _settings(self) -> QSettings:
        return QSettings(self.SETTINGS_ORG, self.SETTINGS_APP)

    def save_layout(self) -> None:
        """
        Remember the arrangement.

        Nothing was persisted before: every launch put the splitter back,
        hid the console, forgot which tab you were on and dropped any dock
        you had arranged.
        """
        settings = self._settings()
        settings.setValue("geometry", self.saveGeometry())
        # Version 2 from R2 on: the docks a version-1 state names are gone,
        # and an older layout is ignored rather than half applied.
        settings.setValue("windowState", self.saveState(self.STATE_VERSION))
        settings.setValue("paneKeys", list(self._grid.keys))
        settings.setValue("paneSources",
                          [source.name for source in self._grid.sources])
        for workspace, side in self._side_panels.items():
            key = self._side_key(workspace)
            settings.setValue(f"{key}/open", side.is_open)
            settings.setValue(f"{key}/tab", side.current)
            settings.setValue(f"{key}/width", side.preferred_width)
        settings.setValue("workspace", self._stack.current.value)

    def restore_layout(self) -> bool:
        """Put it back. Returns whether anything was restored."""
        settings = self._settings()
        geometry = settings.value("geometry")
        state = settings.value("windowState")
        if geometry is None and state is None:
            return False
        if geometry is not None:
            self.restoreGeometry(geometry)
        if state is not None:
            self.restoreState(state, self.STATE_VERSION)
        self._restore_panes(settings.value("paneKeys"),
                            settings.value("paneSources"))
        saved = settings.value("workspace")
        if saved:
            try:
                self._stack.set_current(Workspace(saved))
            except ValueError:
                pass
        self._restore_side_panels(settings)
        self._sync_view_menu()
        return True

    #: The `saveState` version: 2 since the docks went into side panels.
    STATE_VERSION = 2

    #: Each side panel as Reset layout leaves it: (open, tab).
    SIDE_DEFAULTS = {
        Workspace.ANALYSE: (False, "loop"),
        Workspace.MODEL: (True, "properties"),
        Workspace.CONSOLE: (True, "workspace"),
    }

    @staticmethod
    def _side_key(workspace) -> str:
        return f"side/{workspace.name.lower()}"

    def _restore_side_panels(self, settings: QSettings) -> None:
        """
        Each workspace's panel: open, tab and width. Then the keys of the
        docks they replaced, once: ``modelPanel`` (the loop dock) opens
        Analyse's panel on Loop, ``cedricPanel`` Console's on Cedric.
        """
        for workspace, side in self._side_panels.items():
            key = self._side_key(workspace)
            is_open = settings.value(f"{key}/open")
            if is_open is not None:
                side.set_open(_truthy(is_open))
            tab = settings.value(f"{key}/tab")
            if isinstance(tab, str):
                side.set_current(tab)
            try:
                width = int(settings.value(f"{key}/width") or 0)
            except (TypeError, ValueError):
                width = 0
            if width > 0:
                side.set_preferred_width(width)
        for old, workspace, tab in (("modelPanel", Workspace.ANALYSE, "loop"),
                                    ("cedricPanel", Workspace.CONSOLE,
                                     "cedric")):
            if settings.contains(old):
                if _truthy(settings.value(old)):
                    side = self._side_panels[workspace]
                    side.set_current(tab)
                    side.set_open(True)
                settings.remove(old)

    def _reset_side_panels(self) -> None:
        for workspace, (is_open, tab) in self.SIDE_DEFAULTS.items():
            side = self._side_panels[workspace]
            side.set_current(tab)
            side.set_preferred_width(SidePanel.DEFAULT_WIDTH)
            side.set_open(is_open)

    def _restore_panes(self, keys, sources) -> None:
        """
        Put the pane grid back: how many, what each shows, and of which system.

        Saved settings are untrusted input (an older build, a hand-edited
        key), so anything unrecognised is dropped and the grid keeps what it
        has rather than failing the whole restore.
        """
        if isinstance(keys, str):       # QSettings collapses 1-element lists
            keys = [keys]
        if isinstance(sources, str):
            sources = [sources]
        if not keys or len(keys) not in LAYOUTS:
            return
        known = {k.key for k in PANE_KINDS}
        if any(key not in known for key in keys):
            return
        chosen = []
        for name in list(sources or [])[:len(keys)]:
            chosen.append(Source[name] if name in Source.__members__ else None)
        self._grid.set_layout_size(len(keys), tuple(keys), tuple(chosen))
        self._sync_layout_buttons()

    def reset_layout(self) -> None:
        """
        Back to the defaults, and forget what was saved.

        A restored layout can become unusable — a dock dragged off-screen, a
        saved geometry from a monitor that is no longer attached. Without
        this, the only fix is deleting a registry key.
        """
        self._settings().clear()
        self._reset_side_panels()
        self.resize(1400, 850)
        self._grid.set_layout_size(4, DEFAULT_LAYOUT, (None,) * 4)
        self._sync_layout_buttons()
        self._stack.set_current(Workspace.ANALYSE)
        self._sync_view_menu()
        self._status.showMessage("Layout reset", 4000)

    def _sync_view_menu(self) -> None:
        self._sync_side_action()

        current = self._stack.current
        for workspace, action in self._workspace_actions.items():
            action.blockSignals(True)
            action.setChecked(workspace is current)
            action.blockSignals(False)

    def confirm_quit(self) -> bool:
        """
        Settle unsaved work before Evans closes: each script tab, the live
        script and the model, one at a time, saved, discarded or cancelled.
        False means stay open. Asked once, so a restart that asks first
        does not ask again as the window closes.
        """
        if not self._quit_confirmed:
            self._quit_confirmed = (
                self._console.editor.confirm_close_all()
                and self._settle_live()
                and self._settle_model())
        return self._quit_confirmed

    def _settle_live(self) -> bool:
        """The live script's unsaved changes, with its tab in view."""
        live = self._console.live
        if not live.is_unsaved():
            return True
        self._stack.set_current(Workspace.CONSOLE)
        self._console.show_live()
        return live.settle_unsaved()

    def _settle_model(self) -> bool:
        """The model's unsaved changes, with the Model tab in view."""
        if not self._sim_tab.is_unsaved():
            return True
        self._stack.set_current(Workspace.MODEL)
        return self._sim_tab.settle_unsaved()

    def reopen_scripts(self) -> int:
        """The scripts open when Evans last closed, in their tabs again."""
        return self._console.editor.reopen_remembered()

    # ── Crash recovery ───────────────────────────────────────

    def _build_autosave_menu(self) -> QMenu:
        """File ▸ Autosave: on or off, and how often."""
        menu = QMenu("&Autosave for crash recovery", self)
        menu.setToolTipsVisible(True)
        self._act_autosave = QAction("&On", self, checkable=True)
        self._act_autosave.setChecked(recovery.saved_enabled())
        self._act_autosave.setToolTip(
            "Keep a copy of unsaved scripts, the live script and the model, "
            "to offer back if Evans closes without being asked to")
        self._act_autosave.toggled.connect(
            lambda on: self.set_autosave(on, self._autosave_interval))
        menu.addAction(self._act_autosave)
        menu.addSeparator()
        self._autosave_interval = recovery.saved_interval()
        group = QActionGroup(self)
        self._autosave_interval_actions = {}
        for seconds in recovery.INTERVALS:
            label = f"Every {seconds} s" if seconds < 60 \
                else f"Every {seconds // 60} min"
            action = QAction(label, self, checkable=True)
            action.setChecked(seconds == self._autosave_interval)
            action.triggered.connect(
                lambda _c=False, s=seconds:
                self.set_autosave(self._act_autosave.isChecked(), s))
            group.addAction(action)
            menu.addAction(action)
            self._autosave_interval_actions[seconds] = action
        return menu

    def recovery_items(self) -> list:
        """Every document with changes not on disk."""
        return [*self._console.editor.recovery_items(),
                *self._console.live.recovery_items(),
                *self._sim_tab.recovery_items()]

    def start_recovery(self, root=None) -> None:
        """
        At startup: offer what a crash left behind, then start keeping
        copies of this session's unsaved documents (when autosave is on).
        ``root`` is for tests; Evans uses the app data folder.
        """
        self._recovery = recovery.RecoveryController(
            self.recovery_items, root, self._autosave_interval)
        left = self._recovery.orphans()
        if self._act_autosave.isChecked():
            self._recovery.start()
        if left:
            self.offer_recovery(left)

    def set_autosave(self, on: bool, interval: int) -> None:
        self._autosave_interval = interval
        recovery.remember(on, interval)
        if self._autosave_interval_actions.get(interval) is not None:
            self._autosave_interval_actions[interval].setChecked(True)
        controller = getattr(self, "_recovery", None)
        if controller is None:
            return
        controller.set_interval(interval)
        if on and not controller.running:
            controller.start()
            controller.snapshot()
        elif not on and controller.running:
            controller.stop()

    def offer_recovery(self, left) -> str:
        """Ask what to do with what a crash left; returns the answer."""
        items = [item for orphan in left for item in orphan.items]
        choice = self._ask_recovery(items)
        if choice == "restore":
            for item in items:
                self._restore_item(item)
            for orphan in left:
                recovery.discard(orphan)
            self._status.showMessage(
                f"Restored {len(items)} document"
                f"{'s' if len(items) != 1 else ''}; save them to keep them",
                8000)
        elif choice == "discard":
            for orphan in left:
                recovery.discard(orphan)
        # "later": the folders stay, and are offered again at the next start.
        return choice

    def _restore_item(self, item) -> None:
        if item.kind == recovery.SCRIPT:
            self._console.editor.restore_text(
                item.text, item.path, item.extra.get("language", "auto"))
            self._stack.set_current(Workspace.CONSOLE)
        elif item.kind == recovery.LIVE:
            self._console.live.restore_text(item.text, item.path)
        elif item.kind == recovery.MODEL:
            self._sim_tab.restore_model_text(item.text)

    def _ask_recovery(self, items) -> str:
        """'restore', 'discard' or 'later'. A method so tests can answer it."""
        names = "\n".join(
            f"  • {item.title}" + (f"  ({item.path})" if item.path else "")
            for item in items)
        box = QMessageBox(
            QMessageBox.Warning, "Recover unsaved work?",
            "Evans did not close normally last time. These had changes "
            f"that were not saved:\n\n{names}\n\nRestore them? Nothing is "
            "written to your files until you save.", parent=self)
        restore = box.addButton("Restore", QMessageBox.AcceptRole)
        discard = box.addButton("Discard", QMessageBox.DestructiveRole)
        box.addButton("Ask next time", QMessageBox.RejectRole)
        box.setDefaultButton(restore)
        box.exec()
        clicked = box.clickedButton()
        return ("restore" if clicked is restore else
                "discard" if clicked is discard else "later")

    def closeEvent(self, event) -> None:
        if not self.confirm_quit():
            event.ignore()
            return
        # A clean quit: the recovery copies are not needed.
        if getattr(self, "_recovery", None) is not None:
            self._recovery.stop()
        self._console.editor.remember_open()
        self.save_layout()
        # The help window has no parent, so it would keep Evans running.
        if (helper := help.window()) is not None:
            helper.close()
        # "Update when I close Evans": the installer takes over from here.
        self.updater.install_pending()
        super().closeEvent(event)

    # ── Design and compare (what the apps were) ──────────────

    def open_app(self, request: AppRequest):
        """
        The console's app sink: ``sisotool(G)`` at the prompt lands here.

        The three apps are gone as windows. ``sisotool`` and ``pidtuner``
        open the Analyse side panel's Design tab; ``ltiview`` puts the
        systems in a plot pane's Compare set. All three show Analyse, the
        workspace their changes land in.
        """
        opener = {
            "ltiview": self._ltiview,
            "sisotool": self._sisotool,
            "pidtuner": self._pidtuner,
        }[request.app]
        self._stack.set_current(Workspace.ANALYSE)
        return opener(request)

    def show_design(self, mode: str = "gain") -> DesignPanel:
        """The Analyse side panel, open on Design, showing ``mode``."""
        side = self._side_panels[Workspace.ANALYSE]
        if self._stack.current is not Workspace.ANALYSE:
            self._stack.set_current(Workspace.ANALYSE)
        side.set_current("design")
        side.set_open(True)
        self._design.set_mode(mode)
        self._sync_side_action()
        return self._design

    def _apply_design(self, text: str, tf, merge_key: str | None) -> None:
        """The Design tab's live apply: K2 as one (merged) undo step."""
        self.change_loop(text, lambda: self._arch.set_block("K2", tf),
                         merge_key=merge_key)

    def _sisotool(self, request: AppRequest) -> DesignPanel:
        """
        ``sisotool(G)`` / ``sisotool(G, C)``: the plant (and the starting
        compensator, which the Design tab applies live like any other
        change) go into the loop as one step; then Design, Compensator.
        """
        systems = dict(request.systems)
        if "plant" in systems or "compensator" in systems:
            def mutate() -> None:
                if "plant" in systems:
                    self._arch.set_block("G", _as_tf(systems["plant"]))
                if "compensator" in systems:
                    self._arch.set_block("K2",
                                         _as_tf(systems["compensator"]))
            self.change_loop("sisotool", mutate)
        return self.show_design("compensator")

    def _pidtuner(self, request: AppRequest) -> DesignPanel:
        """``pidtuner(G, kind)``: the plant into the loop; Design, PID."""
        systems = dict(request.systems)
        if "plant" in systems:
            plant = _as_tf(systems["plant"])
            self.change_loop("pidtuner",
                             lambda: self._arch.set_block("G", plant))
        design = self.show_design("pid")
        kind = request.options.get("kind")
        if kind:
            design.tuner.set_kind(kind)
        return design

    def _ltiview(self, request: AppRequest):
        """
        ``ltiview(G1, G2, ...)``: the first plot pane compares exactly the
        named systems (they stay in every pane's Compare menu). With no
        systems, it compares the loop's G, L and T.
        """
        pane = self._first_plot_pane()
        if request.systems:
            self._grid.handed.update(request.systems)
            pane.set_compare([("system", name) for name in request.systems])
        else:
            pane.set_compare([("loop", s.name) for s in
                              (Source.PLANT, Source.OPEN_LOOP,
                               Source.CLOSED_LOOP)])
        self._status.showMessage(
            f"Comparing {len(pane.compare_keys)} systems in the "
            f"{pane._kind.label.lower()} pane", 6000)
        return pane

    def _first_plot_pane(self):
        """The first pane that draws curves; pane 1 becomes one if none do."""
        panes = self._grid.plot_panes()
        if panes:
            return panes[0]
        pane = self._grid.panes[0]
        pane.set_kind("step")
        return pane

    def _compare_snapshots(self, _collection: SystemCollection) -> None:
        """The snapshot bar's Compare: tick every snapshot in every plot pane."""
        panes = self._grid.plot_panes() or [self._first_plot_pane()]
        keys = [("snapshot", label) for label in self.snapshots.labels]
        for pane in panes:
            pane.set_compare([*pane.compare_keys,
                              *(k for k in keys if k not in pane.compare_keys)])
        self._status.showMessage(
            f"Comparing {len(keys)} snapshots in {len(panes)} "
            f"pane{'s' if len(panes) > 1 else ''}", 6000)

    def _on_snapshot_restored(self, snapshot) -> None:
        self.change_loop("Restore snapshot")
        self._status.showMessage(f"Restored “{snapshot.label}”", 5000)

    # ── Menus ────────────────────────────────────────────────

    def _build_theme_menu(self) -> QMenu:
        """View ▸ Theme: System / Day / Night, one of them always checked."""
        menu = QMenu("&Theme", self)
        group = QActionGroup(self)
        group.setExclusive(True)
        self._theme_actions: dict[theme.Mode, QAction] = {}
        for mode, text, tip in (
            (theme.Mode.SYSTEM, "&System", "Follow the operating system"),
            (theme.Mode.DAY, "&Day", "Dry concrete: light ground, black ink"),
            (theme.Mode.NIGHT, "&Night", "Asphalt: dark ground, pale ink"),
        ):
            action = QAction(text, self, checkable=True, statusTip=tip)
            action.setChecked(theme.mode() is mode)
            action.triggered.connect(
                lambda _checked=False, m=mode: self.choose_theme(m))
            group.addAction(action)
            menu.addAction(action)
            self._theme_actions[mode] = action
        return menu

    def choose_theme(self, mode: theme.Mode) -> bool:
        """
        A theme picked from the menu: saved, then applied by a restart.

        The theme is not switched in place any more. Restyling every live
        widget and then dragging a splitter could hang the window, so the
        choice goes through a restart, after the user has had the chance to
        save their work. Returns whether a restart was started.
        """
        if mode is theme.mode():
            return False
        if not self._ask_theme_restart(mode):
            self._theme_actions[theme.mode()].setChecked(True)
            return False
        theme.save_mode(mode)
        return self._restart()

    def _ask_theme_restart(self, mode: theme.Mode) -> bool:
        """True for Restart. A method so tests can answer it."""
        t = theme.tokens()
        name = {theme.Mode.SYSTEM: "System", theme.Mode.DAY: "Day",
                theme.Mode.NIGHT: "Night"}[mode]
        box = QMessageBox(self)
        box.setWindowTitle("Change theme")
        box.setTextFormat(Qt.RichText)
        # Weight and colour set outright: the variable sign font ignored a
        # plain <b>, and this is the one phrase the dialog exists to say.
        box.setText(f"Changing to the {name} theme requires "
                    f'<span style="font-weight:800; color:{t.signal};">'
                    f"an app restart</span>.")
        box.setInformativeText(
            "Evans will close and open again. Unsaved models, scripts and "
            "figures are not kept, so save anything you need first.")
        restart = box.addButton("Restart", QMessageBox.AcceptRole)
        back = box.addButton("Go back and save work", QMessageBox.RejectRole)
        restart.setStyleSheet(
            f"QPushButton {{ background: {t.lamp_go}; color: #ffffff; "
            f"border: none; padding: 6px 16px; font-weight: 600; }}")
        back.setStyleSheet(
            f"QPushButton {{ background: {t.hold}; color: {t.on_hold}; "
            f"border: none; padding: 6px 16px; font-weight: 600; }}")
        for button in (restart, back):
            # The uppercase sign font sets "BACK AND" so tight it reads as
            # one word; a little more room between words.
            font = button.font()
            font.setWordSpacing(4)
            button.setFont(font)
        box.setDefaultButton(back)
        box.setEscapeButton(back)
        box.exec()
        return box.clickedButton() is restart

    def _restart(self) -> bool:
        """Start a new Evans with the same arguments, then close this one."""
        if not self.confirm_quit():
            return False
        if getattr(sys, "frozen", False):        # Evans.exe
            program, args = sys.executable, sys.argv[1:]
        else:                                     # python app.py / evans
            program = sys.executable
            args = [os.path.abspath(sys.argv[0]), *sys.argv[1:]]
        if not self._start_detached(program, args):
            QMessageBox.warning(
                self, "Change theme",
                "Evans could not start a new window. The theme is saved and "
                "applies the next time you open Evans.")
            return False
        self.close()
        QApplication.instance().quit()
        return True

    @staticmethod
    def _start_detached(program: str, args: list[str]) -> bool:
        """A method so tests can stop the real relaunch."""
        ok = QProcess.startDetached(program, args, os.getcwd())
        return bool(ok[0] if isinstance(ok, tuple) else ok)

    def _build_menus(self) -> None:
        mb = self.menuBar()

        # File menu
        file_menu = mb.addMenu("&File")
        act_new  = QAction("&New",            self); act_new.setShortcut("Ctrl+N")
        self._act_file_new = act_new
        act_open = QAction("&Open…",          self); act_open.setShortcut("Ctrl+O")
        act_save = QAction("&Save",           self); act_save.setShortcut("Ctrl+S")
        act_save_as = QAction("Save &as…",    self)
        act_save_as.setShortcut("Ctrl+Shift+S")
        # One File menu, three workspaces: each item acts on the page in view
        # (file_open, file_save, file_save_as) and its status tip says which.
        self._act_file_open, self._act_file_save = act_open, act_save
        self._act_file_save_as = act_save_as
        act_quit = QAction("&Quit",           self); act_quit.setShortcut("Ctrl+Q")
        act_new.triggered.connect(self.file_new)
        act_open.triggered.connect(self.file_open)
        act_save.triggered.connect(self.file_save)
        act_save_as.triggered.connect(self.file_save_as)
        act_quit.triggered.connect(self.close)
        for a in [act_new, act_open, act_save, act_save_as, None]:
            if a is None:
                file_menu.addSeparator()
            else:
                file_menu.addAction(a)
        self._recent_menu = file_menu.addMenu("Open &recent")
        self._recent_menu.setToolTipsVisible(True)
        self._recent_menu.aboutToShow.connect(self._fill_recent_menu)
        self._fill_recent_menu()
        self._examples_menu = file_menu.addMenu("E&xamples")
        self._examples_menu.setToolTipsVisible(True)
        self._fill_examples_menu()
        file_menu.addSeparator()
        file_menu.addMenu(self._build_autosave_menu())
        file_menu.addSeparator()
        file_menu.addAction(act_quit)
        self._sync_file_tips()

        # Edit menu: one Undo and Redo for whichever workspace is in view.
        # Analyse undoes loop changes, Model the canvas; the Console's text
        # editors handle Ctrl+Z themselves (the group has no active stack).
        edit_menu = mb.addMenu("&Edit")
        self._undo_group = QUndoGroup(self)
        self._undo_group.addStack(self._loop_undo)
        self._undo_group.addStack(self._sim_tab._canvas.undo_stack)
        act_undo = self._undo_group.createUndoAction(self, "Undo")
        act_undo.setShortcut("Ctrl+Z")
        act_redo = self._undo_group.createRedoAction(self, "Redo")
        act_redo.setShortcuts(["Ctrl+Y", "Ctrl+Shift+Z"])
        self._act_undo, self._act_redo = act_undo, act_redo
        edit_menu.addAction(act_undo)
        edit_menu.addAction(act_redo)
        edit_menu.addSeparator()
        self._edit_menu = edit_menu
        self._undo_group.indexChanged.connect(self._on_undo_index)
        self._sync_undo_group()

        # Export menu
        export_menu = mb.addMenu("&Export")
        act_copy = QAction("&Copy analysis report", self)
        act_copy.setShortcut("Ctrl+Shift+C")
        act_copy.triggered.connect(self._copy_report)
        act_report = QAction("Save analysis &report…", self)
        act_report.triggered.connect(self._save_report)
        act_png = QAction("Export current tab as &PNG…", self)
        act_png.setShortcut("Ctrl+Shift+P")
        act_png.triggered.connect(self._export_plot_png)
        for a in (act_copy, act_report, act_png):
            export_menu.addAction(a)
        export_menu.addSeparator()
        act_diagram = QAction("Model &diagram…", self)
        act_diagram.setToolTip("The Model tab's block diagram as SVG, PDF "
                               "or PNG")
        act_diagram.triggered.connect(self._sim_tab.export_diagram)
        act_print = QAction("Print model diagram…", self)
        act_print.triggered.connect(self._sim_tab.print_diagram)
        act_data = QAction("Model &scope data…", self)
        act_data.setToolTip("The last run's signals as CSV or .mat")
        act_data.triggered.connect(self._sim_tab.export_data)
        for a in (act_diagram, act_print, act_data):
            export_menu.addAction(a)

        # View menu
        view_menu = mb.addMenu("&View")
        act_side = QAction("&Side panel", self, checkable=True)
        act_side.setShortcut("Ctrl+\\")
        act_side.setStatusTip(
            "This workspace's side panel: the loop, the block properties or "
            "the variables, and Cedric")
        act_side.triggered.connect(self.toggle_side_panel)
        self._act_side = act_side
        view_menu.addAction(act_side)

        act_cedric = QAction("&Cedric", self, checkable=True)
        act_cedric.setShortcut("Ctrl+Shift+A")
        act_cedric.setStatusTip(
            "Cedric, the assistant, in this workspace's side panel: ask a "
            "free AI model about your code")
        act_cedric.triggered.connect(self.set_cedric_visible)
        # What the console's tab-bar button says (the menu keeps "Cedric").
        act_cedric.setIconText("Ask Cedric")
        self._act_cedric = act_cedric
        view_menu.addAction(act_cedric)
        self._console.cedric_button.setDefaultAction(act_cedric)
        self._console._style_cedric_button()        # his drawing on both

        view_menu.addSeparator()

        # The three workspaces. Ctrl+1/2/3, plus Ctrl+` for the console
        # because that is the key everyone's fingers already know.
        self._workspace_actions: dict[Workspace, QAction] = {}
        for workspace in Workspace:
            action = QAction(workspace.value, self, checkable=True)
            action.setShortcut(workspace.shortcut)
            action.setStatusTip(workspace.description)
            action.triggered.connect(
                lambda _checked=False, w=workspace:
                self._stack.set_current(w))
            view_menu.addAction(action)
            self._workspace_actions[workspace] = action

        console_shortcut = QAction("Command window", self)
        # On a Mac ⌘` is the system's "next window of this app"; Control-`
        # (Qt's Meta there) is free, and is VS Code's terminal key on a Mac.
        console_shortcut.setShortcut("Meta+`" if keys.is_mac() else "Ctrl+`")
        console_shortcut.triggered.connect(
            lambda: self._stack.set_current(Workspace.CONSOLE))
        self.addAction(console_shortcut)

        view_menu.addSeparator()
        view_menu.addMenu(self._build_theme_menu())
        from .sim import shapes as block_shapes
        act_classic = QAction("&Classic block boxes", self, checkable=True)
        act_classic.setStatusTip(
            "Draw every block on the Model tab as a plain rectangle")
        act_classic.setChecked(block_shapes.classic())
        act_classic.toggled.connect(block_shapes.set_classic)
        self._act_classic_boxes = act_classic
        view_menu.addAction(act_classic)
        act_title_bar = QAction("Integrated &title bar", self, checkable=True)
        act_title_bar.setStatusTip(
            "Menus and window buttons in one strip (Windows)" if
            winframe.supported() else
            "Only on Windows; this system draws its own title bar")
        act_title_bar.setEnabled(winframe.supported())
        act_title_bar.triggered.connect(self.set_integrated_title_bar)
        self._act_title_bar = act_title_bar
        view_menu.addAction(act_title_bar)
        view_menu.addSeparator()
        view_menu.addAction(QAction(
            "&Reset layout", self, triggered=self.reset_layout,
            statusTip="Restore the default window, side panels and panes"))
        view_menu.addSeparator()
        view_menu.addAction(QAction(
            "Send current plant to the console", self,
            triggered=self._push_to_console))

        # Presets menu
        preset_menu = mb.addMenu("&Presets")
        preset_menu.addAction(QAction("1st order  K/(τs+1)", self,
                                       triggered=self._preset_first_order))
        preset_menu.addAction(QAction("2nd order underdamped", self,
                                       triggered=self._preset_so_under))
        preset_menu.addAction(QAction("2nd order overdamped", self,
                                       triggered=self._preset_so_over))
        preset_menu.addAction(QAction("Double integrator 1/s²", self,
                                       triggered=self._preset_double_int))
        preset_menu.addAction(QAction("Unstable plant 1/(s-1)", self,
                                       triggered=self._preset_unstable))
        preset_menu.addAction(QAction("Non-minimum phase (−s+1)/(s+1)", self,
                                       triggered=self._preset_nmp))
        preset_menu.addAction(QAction("Satellite (double integrator)", self,
                                       triggered=self._preset_satellite))

        # Help menu
        # Settings menu: preferences that outlast Reset layout.
        settings_menu = mb.addMenu("&Settings")
        act_snapshots = QAction("Show &snapshot bar", self, checkable=True)
        act_snapshots.setChecked(persist.snapshot_bar())
        act_snapshots.setStatusTip(
            "The Snapshot · Restore · Compare row above the analysis panes")
        act_snapshots.triggered.connect(self.set_snapshot_bar_visible)
        self._act_snapshots = act_snapshots
        settings_menu.addAction(act_snapshots)

        help_menu = mb.addMenu("&Help")
        help_menu.addAction(QAction("Documentation", self, shortcut="F1",
                                     triggered=lambda: help.open_help()))
        help_menu.addSeparator()
        help_menu.addAction(QAction(
            "Check for &updates…", self,
            triggered=lambda: self.updater.check(),
            statusTip="Look for a newer Evans on GitHub"))
        act_auto_update = QAction("Check for updates &automatically", self,
                                  checkable=True)
        act_auto_update.setChecked(persist.update_auto_check())
        act_auto_update.setStatusTip("Once a day, a few seconds after launch")
        act_auto_update.triggered.connect(persist.set_update_auto_check)
        help_menu.addAction(act_auto_update)
        help_menu.addSeparator()
        help_menu.addAction(QAction("About", self,
                                     triggered=self._show_about))

    def _build_status_bar(self) -> None:
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        # The Model page's status line and file name live here, shown only
        # while that page is: a row of their own under the canvas cost the
        # diagram height and left this bar empty.
        model_status, model_file = self._sim_tab.status_widgets()
        self._status.addWidget(model_status, 1)
        self._status.addPermanentWidget(model_file)
        self._sync_model_status()

    def _sync_model_status(self) -> None:
        on_model = self._stack.current is Workspace.MODEL
        for widget in self._sim_tab.status_widgets():
            widget.setVisible(on_model)

    # ── Event handlers ────────────────────────────────────────

    def _on_block_selected(self, block_id: str) -> None:
        bd = self._arch.get_block(block_id)
        self._editor.load_block(block_id, bd.tf, bd.label)
        self._status.showMessage(f"Editing {bd.label}", 3000)

    def _on_signal_selected(self, signal_id: str) -> None:
        self._status.showMessage(f"Signal tap: {signal_id}", 2000)
        self._grid.set_active_signal(signal_id)
        self._grid.refresh(self._arch)

    def _on_tf_edited(self, block_id: str, tf: ctl.TransferFunction) -> None:
        self.change_loop(f"Edit {block_id}",
                         lambda: self._diagram.update_block(block_id, tf))

    def _on_arch_changed(self) -> None:
        self._update_all_tabs()

    def _on_controller_designed(self, tf: ctl.TransferFunction) -> None:
        """Design tab applied a new K2 — sync diagram and all tabs."""
        self.change_loop("Apply controller",
                         lambda: self._diagram.update_block("K2", tf))

    def _refresh_analyse(self) -> None:
        """Refresh every pane of the Analyse page."""
        self._grid.refresh(self._arch)

    def _on_modern_model_sent(self) -> None:
        """The Modern tab pushed its state-space model back as G(s)."""
        self.change_loop("Send model to G")

    def _on_linearised(self, tf, description: str) -> None:
        """
        A model was linearised on the Simulink tab: analyse it here.

        The linearised system becomes the plant G, with the controller reset
        to unity — the loop is already baked into the linearisation, so
        leaving K₂ in place would apply it twice.
        """
        def mutate() -> None:
            self._arch.set_block("G", tf)
            self._arch.set_block("K2", unity())

        self.change_loop("Load linearised model", mutate)
        self._stack.set_current(Workspace.ANALYSE)
        self._status.showMessage(
            "Linearised model loaded as G(s) — " +
            description.splitlines()[0], 8000)

    # ── Loop undo ─────────────────────────────────────────────

    def change_loop(self, text: str, mutate=None, *,
                    merge_key: str | None = None) -> None:
        """
        Change the loop as one undoable step named ``text``.

        ``mutate`` (if any) makes the change. The step starts from the loop
        as last seen (`_loop_baseline`), so a widget that already wrote the
        architecture before telling us is covered too. ``merge_key`` folds
        consecutive changes with the same key into one step (a slider drag).
        """
        before = self._loop_baseline
        if mutate is not None:
            mutate()
        after = session_dict(self._arch)
        if after != before:
            self._loop_undo.push(ReplaceLoop(
                self._arch, before, after, text,
                self._after_loop_change, merge_key))
        self._after_loop_change()

    def _after_loop_change(self) -> None:
        """Show the loop as it now is, and remember it as the baseline."""
        self._loop_baseline = session_dict(self._arch)
        self._diagram.build()
        self._update_all_tabs()
        self._refresh_status()
        self._design.loop_changed()

    def _on_console_executed(self, _result=None) -> None:
        """A console command may have changed ``arch`` behind our back."""
        after = session_dict(self._arch)
        if after == self._loop_baseline:
            return
        self._loop_undo.push(ReplaceLoop(
            self._arch, self._loop_baseline, after, "Console change",
            self._after_loop_change))
        self._loop_baseline = after
        self._diagram.build()
        self._design.loop_changed()

    def _sync_undo_group(self) -> None:
        """Point Edit > Undo at the stack of the workspace in view."""
        group = getattr(self, "_undo_group", None)
        if group is None:
            return
        canvas = self._sim_tab._canvas
        # Descending into a subsystem swaps the canvas's stack; keep the group
        # to the stacks still in use.
        live = {self._loop_undo, canvas.undo_stack,
                *(entry[2] for entry in canvas._stack)}
        for stack in group.stacks():
            if stack not in live:
                group.removeStack(stack)
        for stack in live:
            if stack not in group.stacks():
                group.addStack(stack)
        current = self._stack.current
        if current is Workspace.ANALYSE:
            active = self._loop_undo
        elif current is Workspace.MODEL:
            active = canvas.undo_stack
        else:
            active = None
        if active is not None:
            self._undo_seen[active] = active.index()
        group.setActiveStack(active)

    def _on_undo_index(self, index: int) -> None:
        stack = self._undo_group.activeStack()
        if stack is None:
            return
        seen = self._undo_seen.get(stack, index)
        self._undo_seen[stack] = index
        if index < seen and stack.redoText():
            self._status.showMessage(f"Undo: {stack.redoText()}", 3000)

    # ── Full refresh ──────────────────────────────────────────

    def _update_all_tabs(self) -> None:
        """Refresh what is on screen now; the rest lazily when selected."""
        self._context.refresh()
        self._refresh_analyse()

    def _on_workspace_changed(self, workspace) -> None:
        """Refresh whatever the new page shows, and tell the menu."""
        if workspace is Workspace.ANALYSE:
            self._update_all_tabs()
        elif workspace is Workspace.CONSOLE:
            self._console.focus()
        # Cedric follows the workspace, and the View menu's Side panel and
        # Cedric marks follow its panel (there is no dock state to restore).
        self._place_cedric(workspace)
        self._sync_view_menu()
        self._sync_model_status()
        self._sync_file_tips()
        self._sync_undo_group()
        self._status.showMessage(workspace.description, 4000)

    def show_workspace(self, workspace) -> None:
        self._stack.set_current(workspace)

    def _run_from_help(self, source: str):
        """A help page's Run: the example runs at the prompt, in view."""
        self._stack.set_current(Workspace.CONSOLE)
        if self.isMinimized():
            self.showNormal()
        self.raise_()
        self.activateWindow()
        return self._console.execute(source)

    def _push_to_console(self) -> None:
        """Put the current plant and loop into the workspace under short names."""
        self._console.push(
            arch=self._arch,
            G=self._arch.block_tf("G"),
            K2=self._arch.block_tf("K2"),
            L=self._arch.loop_tf(),
            T=self._arch.get_closed_loop_tf("r", "y"),
            model=self._sim_tab._canvas.root_model(),
        )
        self._stack.set_current(Workspace.CONSOLE)
        self._status.showMessage(
            "G, K2, L, T, arch and model are now in the workspace", 6000)

    def _refresh_status(self) -> None:
        """
        Refresh the context bar.

        The status bar used to carry ``G=[1, 2]/[1, 3, 3, 1]`` — coefficient
        arrays, no factorisation, no verdict. That job belongs to the context
        bar now; the status bar is for transient messages.
        """
        self._context.refresh()

    # ── File I/O ──────────────────────────────────────────────

    def _new_session(self) -> None:
        # The same architecture object, loaded with the default loop: the undo
        # stack, the panes, the diagram, the snapshot bar and the console all
        # hold it, and none of them has to be handed a new one.
        fresh = session_dict(CourseArchitecture(
            G  = first_order(1.0, 1.0),
            K2 = unity(), K1 = unity(), H  = unity(),
        ))
        self.change_loop("New loop",
                         lambda: load_session_dict(self._arch, fresh))

    def _save_session(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save loop", "", "Loop files (*.json)")
        if not path:
            return
        Path(path).write_text(
            json.dumps(session_dict(self._arch), indent=2), encoding="utf-8")
        self._status.showMessage(f"Saved to {path}", 4000)

    def _open_session(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Open loop", "", "Loop files (*.json)")
        if not path:
            return
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self.change_loop("Open loop",
                             lambda: load_session_dict(self._arch, data))
            self._status.showMessage(f"Loaded {path}", 4000)
        except Exception as exc:
            QMessageBox.critical(self, "Load error", str(exc))

    # The File menu acts on the workspace in view. Tests patch the dialogs the
    # targets open (QFileDialog), never these dispatchers.

    def file_new(self) -> None:
        """File ▸ New: a default loop, an untitled model, or a new script
        (a live script when the Live tab is showing)."""
        workspace = self._stack.current
        if workspace is Workspace.MODEL:
            self._sim_tab.new_model()
        elif workspace is Workspace.CONSOLE:
            if self._console.live_active:
                self._console.live.new_document()
            else:
                self._console.show_script()
                self._console.editor.new_document()
        else:
            self._new_session()

    def file_open(self) -> None:
        """File ▸ Open…: a loop session, a model or a script, by workspace."""
        workspace = self._stack.current
        if workspace is Workspace.MODEL:
            self._sim_tab.open_model()
        elif workspace is Workspace.CONSOLE:
            self._console.editor.open_dialog()
        else:
            self._open_session()

    def file_save(self) -> None:
        """File ▸ Save: the loop, the model or the current script."""
        workspace = self._stack.current
        if workspace is Workspace.MODEL:
            self._sim_tab.save_model()
        elif workspace is Workspace.CONSOLE:
            self._console.editor.save()
        else:
            self._save_session()

    def file_save_as(self) -> None:
        """File ▸ Save as…: asks for a file, whichever workspace is in view."""
        workspace = self._stack.current
        if workspace is Workspace.MODEL:
            self._sim_tab.save_model_as()
        elif workspace is Workspace.CONSOLE:
            self._console.editor.save_as()
        else:
            self._save_session()        # a session is always saved by name

    _FILE_TIPS = {
        Workspace.ANALYSE: ("Open a saved loop", "Save the loop"),
        Workspace.MODEL: ("Open a model", "Save the model"),
        Workspace.CONSOLE: ("Open a script", "Save the script"),
    }

    _NEW_TIPS = {
        Workspace.ANALYSE: "Start again from the default loop",
        Workspace.MODEL: "A new, untitled model",
        Workspace.CONSOLE: "A new script (a live script on the Live tab)",
    }

    def _sync_file_tips(self) -> None:
        open_tip, save_tip = self._FILE_TIPS[self._stack.current]
        self._act_file_new.setStatusTip(self._NEW_TIPS[self._stack.current])
        self._act_file_open.setStatusTip(open_tip)
        self._act_file_save.setStatusTip(save_tip)
        self._act_file_save_as.setStatusTip(save_tip + " under a new name")

    # ── files dropped on the window ─────────────────────────────

    @staticmethod
    def _dropped_files(mime) -> list[Path]:
        if not mime.hasUrls():
            return []
        return [Path(url.toLocalFile()) for url in mime.urls()
                if url.isLocalFile()]

    def dragEnterEvent(self, event) -> None:
        if self._dropped_files(event.mimeData()):
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        paths = self._dropped_files(event.mimeData())
        if paths:
            event.acceptProposedAction()
            self.open_files(paths)

    def open_files(self, paths) -> None:
        """Open each file where it belongs (models on Model, scripts on Console)."""
        for path in paths:
            self.open_recent(path)

    def _fill_examples_menu(self) -> None:
        """One entry per example model; each opens on the Model tab."""
        from ..examples import examples
        menu = self._examples_menu
        menu.clear()
        for example in examples():
            action = QAction(example.title, menu)
            action.setToolTip(example.summary)
            action.triggered.connect(
                lambda _checked=False, e=example: self.open_example(e))
            menu.addAction(action)
        if menu.isEmpty():
            empty = QAction("No examples installed", menu)
            empty.setEnabled(False)
            menu.addAction(empty)

    def open_example(self, example) -> bool:
        """
        Open an example model on the Model tab, as a copy to change.
        False when the user kept the unsaved model on the canvas instead.
        """
        if not self._settle_model():
            return False
        # The Model page first: a canvas that is not on screen has no size to
        # fit to (SimTab.load_model also fits when it is next shown).
        self._stack.set_current(Workspace.MODEL)
        self._sim_tab.load_model(example.path, remember=False)
        self._status.showMessage(f"{example.title}: {example.summary}", 8000)
        return True

    def _fill_recent_menu(self) -> None:
        """
        List the recent scripts and models, newest first.

        Rebuilt each time the menu opens, so a file deleted since it was
        opened is simply not offered.
        """
        menu = self._recent_menu
        menu.clear()
        paths = self.recent_files.paths()
        for n, path in enumerate(paths, start=1):
            prefix = f"&{n}  " if n < 10 else f"{n}  "
            action = QAction(f"{prefix}{path.name}   —   {path.parent}", menu)
            action.setToolTip(str(path))
            action.triggered.connect(
                lambda _checked=False, p=path: self.open_recent(p))
            menu.addAction(action)
        if not paths:
            empty = QAction("No recent files", menu)
            empty.setEnabled(False)
            menu.addAction(empty)
        menu.addSeparator()
        clear = QAction("&Clear recent files", menu)
        clear.setEnabled(bool(paths))
        clear.triggered.connect(self.recent_files.clear)
        menu.addAction(clear)

    def open_recent(self, path: str | Path) -> bool:
        """
        Open a recent file where it belongs: a model on the Model canvas, a
        script in the Console's Script tab. Returns whether it opened.
        """
        # A .fmdl since saved as .evx opens as the .evx.
        path = preferred_file(path)
        if not path.is_file():
            self.recent_files.paths()          # forgets it
            self._status.showMessage(f"{path} no longer exists", 6000)
            return False
        if is_model_file(path):
            if not self._settle_model():
                return False
            self._stack.set_current(Workspace.MODEL)
            self._sim_tab.load_model(path)
        else:
            try:
                self._console.editor.load_file(path)
            except (OSError, UnicodeDecodeError) as exc:
                QMessageBox.critical(self, "Open error", str(exc))
                return False
            self._stack.set_current(Workspace.CONSOLE)
            self._console.show_script()
        return True

    # ── Export ────────────────────────────────────────────────

    def _copy_report(self) -> None:
        """Put the full text report on the clipboard."""
        report = text_report(self._arch)
        QApplication.clipboard().setText(report)
        self._status.showMessage(
            f"Analysis report copied to clipboard ({len(report)} chars)", 5000)

    def _save_report(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save analysis report", "evans-report.txt",
            "Text files (*.txt)")
        if not path:
            return
        Path(path).write_text(text_report(self._arch), encoding="utf-8")
        self._status.showMessage(f"Report written to {path}", 4000)

    def _export_plot_png(self) -> None:
        """Export the analysis pane grid as a PNG."""
        widget = self._grid
        path, _ = QFileDialog.getSaveFileName(
            self, "Export analysis as PNG", "evans-analysis.png",
            "PNG images (*.png)")
        if not path:
            return
        if widget.grab().save(path):
            self._status.showMessage(f"Image written to {path}", 4000)
        else:
            QMessageBox.warning(self, "Export failed",
                                f"Qt could not write {path}")

    # ── Presets ───────────────────────────────────────────────

    def _load_preset_G(self, tf: ctl.TransferFunction) -> None:
        def mutate() -> None:
            self._arch.set_block("G", tf)
            self._arch.set_block("K2", unity())

        self.change_loop("Load preset", mutate)

    def _preset_first_order(self):  self._load_preset_G(first_order(1.0, 1.0))
    def _preset_so_under(self):     self._load_preset_G(second_order(1.0, 0.2, 2.0))
    def _preset_so_over(self):      self._load_preset_G(second_order(1.0, 2.0, 1.0))
    def _preset_double_int(self):   self._load_preset_G(ctl.TransferFunction([1],[1,0,0]))
    def _preset_unstable(self):     self._load_preset_G(ctl.TransferFunction([1],[1,-1]))
    def _preset_nmp(self):          self._load_preset_G(ctl.TransferFunction([-1,1],[1,1]))
    def _preset_satellite(self):    self._load_preset_G(ctl.TransferFunction([1],[1,0,0]))

    # ── About ────────────────────────────────────────────────

    def _show_about(self) -> None:
        QMessageBox.about(
            self, "About Evans",
            "Evans — Classical & Modern Control\n\n"
            "Built for the CLACO course (Master Automatique et Robotique).\n\n"
            "Stack: Python 3.12 · python-control · PySide6 · pyqtgraph · sympy\n\n"
            "Architecture: 2-DOF feedback + feedforward (ch.5)\n"
            "Analysis: Bode, Nyquist, Nichols, Routh, Root Locus,\n"
            "          step/impulse/ramp metrics, PID tuning (Z-N).\n\n"
            "Named after Walter R. Evans, who invented the root locus.\n\n"
            "MATLAB and Simulink are registered trademarks of The MathWorks, Inc. Evans is an independent project, not affiliated with or endorsed by MathWorks."
        )


# ── Helpers ───────────────────────────────────────────────────

def _truthy(value) -> bool:
    """A saved bool: QSettings hands it back as "true" on some backends."""
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes")
    return bool(value)


def _tf_short(tf: ctl.TransferFunction) -> str:
    """Very short string for status bar."""
    num = tf.num[0][0]
    den = tf.den[0][0]
    n = ", ".join(f"{c:.3g}" for c in num)
    d = ", ".join(f"{c:.3g}" for c in den)
    return f"[{n}]/[{d}]"


def _as_tf(system) -> ctl.TransferFunction:
    """A console system as a transfer function: a state space converts."""
    if isinstance(system, ctl.TransferFunction):
        return system
    if hasattr(system, "A"):
        return ctl.ss2tf(system)
    return ctl.tf(float(system), 1)
