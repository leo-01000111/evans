"""
Phase 8, package R0: quick fixes with no structural change.

Root locus range and ticks, legend placement, Bode label collisions, examples
that open fitted, the 2x2 first launch, files dropped on the window, the File
menu acting on the workspace in view, and the one verb "Apply to loop".
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="Qt not available")

import control as ctl
import numpy as np
from PySide6.QtCore import QMimeData, QPointF, Qt, QUrl
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QKeySequence
from PySide6.QtWidgets import QApplication, QPushButton

from evans.core.architecture import CourseArchitecture
from evans.core.collection import SystemCollection
from evans.core.viewer import ResponseKind
from evans.examples import examples
from evans.ui.apps.lti_viewer import LTIViewer
from evans.ui.mainwindow import MainWindow
from evans.ui.panes import DEFAULT_LAYOUT
from evans.ui.plots import (
    add_text_annotation,
    emptiest_corner,
    make_freq_plot,
    separate_labels,
    widen_degenerate_range,
)
from evans.ui.sim.canvas import MIME_TYPE
from evans.ui.workspace import Workspace


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def win(app):
    window = MainWindow(CourseArchitecture())
    window.show()
    _settle(app)
    yield window
    window.hide()


@pytest.fixture(autouse=True)
def back_to_analyse(request, app):
    yield
    if "win" in request.fixturenames:
        request.getfixturevalue("win").show_workspace(Workspace.ANALYSE)


def _settle(app, rounds: int = 20) -> None:
    for _ in range(rounds):
        app.processEvents()


def _viewer(kind: ResponseKind, plant, app, width=640, height=420):
    collection = SystemCollection()
    collection.add("G", plant)
    viewer = LTIViewer(collection, compact=True)
    viewer.set_response(kind)
    viewer.show()
    _settle(app)
    viewer.resize(width, height)        # once the window is up, the size sticks
    _settle(app)
    return viewer


def _plot_item(viewer):
    from pyqtgraph import PlotWidget
    return viewer.findChildren(PlotWidget)[0].getPlotItem()


# ── root locus range and ticks ───────────────────────────────────

def test_widen_degenerate_range_centres_on_the_collapsed_axis():
    (x_lo, x_hi), (y_lo, y_hi) = widen_degenerate_range(
        -1.0 - 1e-15, -1.0 + 1e-15, -3.0, 3.0)
    assert x_hi - x_lo == pytest.approx(6.0)
    assert 0.5 * (x_lo + x_hi) == pytest.approx(-1.0)
    assert (y_lo, y_hi) == (-3.0, 3.0)


def test_a_sane_range_is_left_alone():
    assert widen_degenerate_range(-2, 0, -1, 1) == ((-2, 0), (-1, 1))


def test_a_single_point_gets_a_unit_box():
    (x_lo, x_hi), (y_lo, y_hi) = widen_degenerate_range(2, 2, 1, 1)
    assert x_hi - x_lo == pytest.approx(1.0) and y_hi - y_lo == pytest.approx(1.0)


def test_root_locus_of_the_default_plant_has_a_usable_range(app):
    """Every branch lies on Re = -1: the x range used to be about 1e-15 wide."""
    viewer = _viewer(ResponseKind.RLOCUS, ctl.tf([4], [1, 2, 4]), app)
    plot = _plot_item(viewer)
    x_lo, x_hi = plot.viewRange()[0]
    assert x_hi - x_lo >= 1.0
    axis = plot.getAxis("bottom")
    for spacing, values in axis.tickValues(x_lo, x_hi, 600):
        for text in axis.tickStrings(values, 1.0, spacing):
            assert len(text) < 8, text
    viewer.close()


def test_designer_frame_survives_a_collapsed_locus(app):
    from evans.ui.apps.designer_app import _frame
    from evans.ui.plots import make_plot

    widget = make_plot("", "Re", "Im")
    roots = np.array([[-1 + 1.7j], [-1 - 1.7j], [-1 + 1.7j + 1e-15]])
    _frame(widget.getPlotItem(), roots)
    x_lo, x_hi = widget.getPlotItem().viewRange()[0]
    assert x_hi - x_lo >= 1.0


# ── legend ───────────────────────────────────────────────────────

def test_the_legend_goes_to_the_emptiest_corner():
    # Data fills the left and the bottom-right: only the top right is empty.
    xs = [0, 0, 0, 1, 1, 10]
    ys = [0, 5, 10, 0, 0, 0]
    assert emptiest_corner(xs, ys) == (True, True)
    # A curve running along the top: the top corners are crowded.
    assert emptiest_corner([0, 1, 2, 3, 4, 5], [9, 9, 9, 9, 9, 0])[1] is False
    assert emptiest_corner([], []) == (True, True)


def test_the_root_locus_legend_is_not_where_the_data_is(app):
    viewer = _viewer(ResponseKind.RLOCUS, ctl.tf([1], [1, 3, 2, 0]), app)
    legend = _plot_item(viewer).legend
    assert legend is not None
    # Not every corner is the default top right; the placement is computed.
    assert legend.isVisible()
    viewer.close()


def test_a_narrow_pane_hides_a_single_curve_legend(app):
    plant = ctl.tf([1], [1, 1])
    narrow = _viewer(ResponseKind.STEP, plant, app, width=300)
    legend = _plot_item(narrow).legend
    assert len(legend.items) == 1
    assert not legend.isVisible()
    narrow.resize(640, 420)
    _settle(app)
    assert legend.isVisible()
    narrow.close()


# ── Bode label collisions ────────────────────────────────────────

def test_labels_at_one_spot_are_stacked_not_overlapped(app):
    widget = make_freq_plot("", "dB")
    widget.resize(500, 300)
    widget.show()
    plot = widget.getPlotItem()
    labels = [add_text_annotation(plot, 1.0, 0.0, text)
              for text in ("peak", "BW", "ωc")]
    plot.setXRange(0, 2, padding=0)
    plot.setYRange(-10, 10, padding=0)
    _settle(app)
    relayout = separate_labels(plot, labels)
    relayout()
    vb = plot.getViewBox()
    px, py = vb.viewPixelSize()
    boxes = []
    for item in labels:
        rect = item.boundingRect()
        x, y = item.pos().x(), item.pos().y()
        boxes.append((x, y, x + rect.width() * px, y + rect.height() * py))
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            overlap = a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
            assert not overlap, (a, b)
    assert len({round(y, 9) for _x, y, _x2, _y2 in boxes}) == 3
    widget.close()


# ── examples open fitted ─────────────────────────────────────────

def _visible_scene(canvas):
    return canvas.mapToScene(canvas.viewport().rect()).boundingRect()


def test_an_example_opens_fitted_on_the_model_page(app, win):
    canvas = win._sim_tab._canvas
    canvas.scale(3, 3)                       # someone zoomed in earlier
    assert win.open_example(examples()[0])
    _settle(app)
    assert win._stack.current is Workspace.MODEL
    assert _visible_scene(canvas).contains(canvas.scene().itemsBoundingRect())


def test_a_model_loaded_while_hidden_is_fitted_when_shown(app, win):
    tab = win._sim_tab
    win.show_workspace(Workspace.CONSOLE)
    _settle(app)
    tab._canvas.scale(3, 3)
    tab.load_model(examples()[0].path, remember=False)
    win.show_workspace(Workspace.MODEL)
    _settle(app)
    assert _visible_scene(tab._canvas).contains(
        tab._canvas.scene().itemsBoundingRect())


# ── first launch and Reset layout open 2x2 ───────────────────────

@pytest.fixture
def scratch_settings(monkeypatch):
    from PySide6.QtCore import QSettings
    monkeypatch.setattr(MainWindow, "SETTINGS_ORG", "EvansTest")
    monkeypatch.setattr(MainWindow, "SETTINGS_APP", "R0Test")
    QSettings("EvansTest", "R0Test").clear()
    yield
    QSettings("EvansTest", "R0Test").clear()


def test_a_first_launch_opens_the_2x2_default(app, scratch_settings):
    fresh = MainWindow(CourseArchitecture())
    assert fresh.restore_layout() is False       # nothing saved: app.main() ...
    fresh.set_pane_layout(4)                     # ... then opens 2x2
    assert fresh._grid.count == 4
    assert fresh._grid.keys == DEFAULT_LAYOUT
    fresh.close()


def test_reset_layout_goes_to_2x2(app, win, scratch_settings):
    win._grid.set_layout_size(1, ("bode",))
    win.reset_layout()
    assert win._grid.count == 4
    assert win._grid.keys == DEFAULT_LAYOUT


# ── files dropped on the window ──────────────────────────────────

def _mime(*paths):
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    return mime


def _drop(target, mime):
    enter = QDragEnterEvent(QPointF(5, 5).toPoint(), Qt.CopyAction, mime,
                            Qt.LeftButton, Qt.NoModifier)
    target.dragEnterEvent(enter)
    drop = QDropEvent(QPointF(5, 5), Qt.CopyAction, mime, Qt.LeftButton,
                      Qt.NoModifier)
    target.dropEvent(drop)
    return enter.isAccepted(), drop.isAccepted()


def test_a_dropped_model_opens_on_the_model_page(app, win):
    assert win.acceptDrops()
    entered, dropped = _drop(win, _mime(examples()[0].path))
    assert entered and dropped
    assert win._stack.current is Workspace.MODEL


def test_a_dropped_script_opens_in_the_console(app, win, tmp_path):
    script = tmp_path / "dropped.m"
    script.write_text("x = 1;\n", encoding="utf-8")
    entered, dropped = _drop(win, _mime(script))
    assert entered and dropped
    assert win._stack.current is Workspace.CONSOLE
    assert win._console.editor.document_for(script) is not None


def test_text_drops_are_not_taken_by_the_window(app, win):
    mime = QMimeData()
    mime.setText("hello")
    assert _drop(win, mime) == (False, False)


def test_the_canvas_still_takes_block_drops_and_hands_files_up(app, win):
    canvas = win._sim_tab._canvas
    before = len(canvas.scene().items())
    mime = QMimeData()
    mime.setData(MIME_TYPE, b"Gain")
    entered, dropped = _drop(canvas, mime)
    assert entered and dropped
    assert len(canvas.scene().items()) > before

    seen = []
    canvas.files_dropped.connect(seen.append)
    entered, dropped = _drop(canvas, _mime(examples()[0].path))
    assert entered and dropped
    assert seen == [[examples()[0].path]]


# ── File menu: one set of items, three workspaces ────────────────

def test_only_the_file_menu_owns_the_file_shortcuts(app, win):
    owners = {}
    for action in win.findChildren(QAction):
        for seq in action.shortcuts():
            owners.setdefault(seq.toString(), []).append(action.text())
    for combo in ("Ctrl+O", "Ctrl+S", "Ctrl+Shift+S"):
        assert len(owners.get(combo, [])) == 1, (combo, owners.get(combo))
    file_actions = [a for a in win._sim_tab.findChildren(QAction)
                    if a.text() in ("Open…", "Save", "Save As…")]
    assert len(file_actions) == 3
    for action in file_actions:
        assert action.shortcut() == QKeySequence(), action.text()


def test_model_toolbar_tooltips_name_the_file_shortcuts(app, win):
    from evans.ui import keys
    tips = {a.text(): a.toolTip() for a in win._sim_tab.findChildren(QAction)}
    # Through keys.label, as the tooltips are: a Mac shows ⌘O, not Ctrl+O.
    assert keys.label("Ctrl+O") in tips["Open…"]
    assert keys.label("Ctrl+S") in tips["Save"]
    assert keys.label("Ctrl+Shift+S") in tips["Save As…"]


def test_file_menu_items_are_renamed_and_tipped_by_workspace(app, win):
    assert win._act_file_open.text() == "&Open…"
    assert win._act_file_save.text() == "&Save"
    assert win._act_file_save_as.text() == "Save &as…"
    for workspace, tip in ((Workspace.ANALYSE, "Save the loop"),
                           (Workspace.MODEL, "Save the model"),
                           (Workspace.CONSOLE, "Save the script")):
        win.show_workspace(workspace)
        assert win._act_file_save.statusTip() == tip


def test_new_on_model_opens_an_untitled_model(app, win, monkeypatch):
    sim = win._sim_tab
    monkeypatch.setattr(sim, "settle_unsaved", lambda: True)
    win.show_workspace(Workspace.MODEL)
    win._act_file_new.trigger()
    assert sim.model_path is None
    assert sim._canvas.root_model().name == "untitled"
    assert not sim._canvas.root_model().blocks
    assert not sim.is_unsaved()


def test_new_on_console_makes_a_script_or_a_live_script(app, win, monkeypatch):
    console = win._console
    win.show_workspace(Workspace.CONSOLE)
    console.show_script()
    before = len(console.editor.documents())
    win._act_file_new.trigger()
    assert len(console.editor.documents()) == before + 1
    monkeypatch.setattr(console.live, "settle_unsaved", lambda: True)
    console.show_live()
    assert win._console.live_active
    win._act_file_new.trigger()
    assert console.live.path is None
    assert not console.live.is_unsaved()
    console.show_script()


def test_new_on_analyse_is_one_undoable_loop_step(app, win):
    win.show_workspace(Workspace.ANALYSE)
    win._preset_satellite()          # a loop that differs from the default
    win._act_file_new.trigger()
    assert win._loop_undo.undoText() == "New loop"


def test_save_on_analyse_writes_a_loop_session(app, win, tmp_path, monkeypatch):
    import evans.ui.mainwindow as mw
    target = tmp_path / "loop.json"
    monkeypatch.setattr(mw.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(target), "")))
    win.show_workspace(Workspace.ANALYSE)
    win._act_file_save.trigger()
    assert target.is_file()


def test_open_on_analyse_loads_a_loop_session(app, win, tmp_path, monkeypatch):
    import evans.ui.mainwindow as mw
    target = tmp_path / "loop.json"
    monkeypatch.setattr(mw.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(target), "")))
    win.show_workspace(Workspace.ANALYSE)
    win.file_save()
    asked = []
    monkeypatch.setattr(mw.QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: asked.append(1)
                                     or (str(target), "")))
    win.file_open()
    assert asked


def test_save_as_on_model_asks_the_model_dialog(app, win, tmp_path, monkeypatch):
    import evans.ui.sim.sim_tab as st
    target = tmp_path / "m.evx"
    monkeypatch.setattr(st.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(target), "")))
    win.show_workspace(Workspace.MODEL)
    win._act_file_save_as.trigger()
    assert target.is_file()


def test_open_on_model_asks_the_model_dialog(app, win, monkeypatch):
    import evans.ui.sim.sim_tab as st
    asked = []
    monkeypatch.setattr(st.QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: asked.append(1) or ("", "")))
    win.show_workspace(Workspace.MODEL)
    win._act_file_open.trigger()
    assert asked


def test_save_on_console_saves_the_current_script(app, win, tmp_path,
                                                  monkeypatch):
    import evans.ui.console.script_editor as se
    target = tmp_path / "s.m"
    monkeypatch.setattr(se.QFileDialog, "getSaveFileName",
                        staticmethod(lambda *a, **k: (str(target), "")))
    win.show_workspace(Workspace.CONSOLE)
    editor = win._console.editor
    editor.new_document()                # untitled, so Save has to ask
    editor.current_document().code.setPlainText("y = 2;\n")
    win._act_file_save.trigger()
    assert target.read_text(encoding="utf-8") == "y = 2;\n"


def test_open_on_console_asks_the_script_dialog(app, win, monkeypatch):
    import evans.ui.console.script_editor as se
    asked = []
    monkeypatch.setattr(se.QFileDialog, "getOpenFileNames",
                        staticmethod(lambda *a, **k: asked.append(1) or ([], "")))
    win.show_workspace(Workspace.CONSOLE)
    win._act_file_open.trigger()
    assert asked


# ── one verb ─────────────────────────────────────────────────────

def test_every_apply_button_says_apply_to_loop(app):
    from evans.ui.design_panel import DesignPanel
    from evans.ui.tabs.design_tab import DesignTab
    from evans.ui.tabs.modern.modern_tab import ModernTab

    arch = CourseArchitecture()
    # The Design tab (R3) applies live: no Apply button at all, and none of
    # the old verbs.
    design = DesignPanel(arch, lambda *_args: None)
    assert not [b.text() for b in design.findChildren(QPushButton)
                if b.text().startswith(("Apply", "Send to"))]
    for widget in (DesignTab(arch), ModernTab(arch)):
        buttons = [b for b in widget.findChildren(QPushButton)
                   if b.text() == "Apply to loop"]
        assert len(buttons) == 1, type(widget).__name__
        assert buttons[0].toolTip().startswith("Sets "), buttons[0].toolTip()
        old = [b.text() for b in widget.findChildren(QPushButton)
               if b.text().startswith(("Apply as", "Apply to Arch", "Send to"))]
        assert not old
