"""
What the apps became, as widgets: do they build, redraw and stay wired?

Since R3 the Control System Designer and the PID Tuner are the Analyse side
panel's Design tab (Gain · Compensator · PID), writing K₂ live through
`MainWindow.change_loop`; the LTI Viewer is the plot panes' Compare menu.
The arithmetic is tested in ``test_apps.py``. What is left here is what only a
widget can get wrong — a signal connected to the wrong slot, a stale reference
after a rebuild, a re-read that moves a slider under the user's hand, a panel
that fails silently instead of showing its banner.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("PySide6", reason="Qt not available")

import control as ctl
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from evans.console.apps import AppRequest
from evans.core.architecture import CourseArchitecture
from evans.core.collection import SystemCollection
from evans.core.designer import closed_loop_poles
from evans.core.session import session_dict
from evans.core.tf_utils import second_order, unity
from evans.core.viewer import CHARACTERISTICS, ResponseKind
from evans.ui.apps.designer_app import LOCUS_HEIGHT
from evans.ui.apps.lti_viewer import LTIViewer
from evans.ui.apps.pid_tuner import PLOT_MIN_HEIGHT, PLOT_VIEWS
from evans.ui.design_panel import APPLY_INTERVAL_MS
from evans.ui.guard import ErrorBanner
from evans.ui.mainwindow import MainWindow
from evans.ui.workspace import Workspace

LOCUS_PLANT = ctl.tf([1], [1, 3, 2, 0])
PLANT = second_order(1.0, 0.5, 2.0)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(scope="module")
def win(app):
    """
    One window for the module.

    Building and tearing down a whole widget tree per test inside a single
    QApplication is what produced access violations on Windows; the state is
    reset between tests instead.
    """
    window = MainWindow(CourseArchitecture(G=PLANT))
    window.resize(1500, 900)
    window.show()
    _settle(app)
    yield window
    window.hide()


@pytest.fixture(autouse=True)
def reset(request, app):
    if "win" not in request.fixturenames:
        yield
        return
    window = request.getfixturevalue("win")
    window.show_workspace(Workspace.ANALYSE)
    window.side_panel_of(Workspace.ANALYSE).set_open(False)
    window.snapshots.clear()
    window._snapshot_bar.refresh()
    window._grid.handed.clear()
    window._grid.set_layout_size(4, ("step", "bode", "rlocus", "metrics"),
                                 (None,) * 4)
    # The Design tab's widgets outlive a test: put the tuner's sliders and
    # type back without applying them.
    tuner = window._design.tuner
    tuner._quiet = True
    tuner._speed.setValue(0)
    tuner._transient.setValue(50)
    tuner._tf_spin.setValue(0.0)
    tuner._quiet = False
    tuner.set_kind("PI")
    tuner.set_plot_view(ResponseKind.STEP)
    for block, tf in (("G", PLANT), ("K1", unity()), ("K2", unity()),
                      ("H", unity())):
        window._arch.set_block(block, tf)
    window._after_loop_change()
    window._loop_undo.clear()
    for banner in window.findChildren(ErrorBanner):
        banner.clear()
    _settle(app)
    yield


def _settle(app, rounds: int = 20) -> None:
    for _ in range(rounds):
        app.processEvents()


def _wait(app, ms: int) -> None:
    QTest.qWait(ms)
    _settle(app, 5)


def _banners_clean(widget) -> None:
    failed = [b.message for b in widget.findChildren(ErrorBanner)
              if b.has_error]
    assert not failed, failed[0]


def _k2_gain(win) -> float:
    return float(ctl.dcgain(win._arch.block_tf("K2")))


def _designer(app, win, mode: str = "gain"):
    design = win.show_design(mode)
    _settle(app, 10)
    return design.designer


def _tuner(app, win):
    design = win.show_design("pid")
    _settle(app, 10)
    return design.tuner


# ──────────────────────────────────────────────────────────────
#  The viewer, as the panes' renderer
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def viewer(app):
    widget = LTIViewer(SystemCollection())
    widget.collection.add("a", ctl.tf([1], [1, 1]))
    widget.collection.add("b", ctl.tf([2], [1, 2]))
    widget.refresh()
    widget.show()
    _settle(app, 5)
    yield widget
    widget.hide()
    widget.deleteLater()


def test_the_viewer_renders_every_response_kind(app, viewer):
    for kind in ResponseKind:
        viewer._kind_combo.setCurrentText(kind.value)
        for characteristic in CHARACTERISTICS[kind]:
            viewer.set_characteristic(characteristic, True)
        _settle(app, 3)
        _banners_clean(viewer)
        assert viewer._plot_lay.count() >= 1, f"{kind.value} drew nothing"


def test_the_response_kind_survives_the_combo_round_trip(app, viewer):
    """
    Qt hands a ``str``-mixin enum back as a plain ``str``, which compares
    equal everywhere and then fails on ``.value`` three calls later. The kind
    is rebuilt from the text for that reason.
    """
    viewer._kind_combo.setCurrentText(ResponseKind.NICHOLS.value)
    assert isinstance(viewer._kind, ResponseKind)
    assert viewer._kind is ResponseKind.NICHOLS


def test_characteristics_that_do_not_apply_are_dropped_on_switching(
        app, viewer):
    from evans.core.viewer import Characteristic

    viewer._kind_combo.setCurrentText(ResponseKind.STEP.value)
    viewer.set_characteristic(Characteristic.RISE, True)
    assert Characteristic.RISE in viewer._characteristics
    viewer._kind_combo.setCurrentText(ResponseKind.NYQUIST.value)
    assert Characteristic.RISE not in viewer._characteristics
    _banners_clean(viewer)


def test_unchecking_a_system_removes_its_curve(app, viewer):
    viewer._list.item(0).setCheckState(Qt.Unchecked)
    _settle(app, 3)
    assert [e.name for e in viewer.collection.visible] == ["b"]
    _banners_clean(viewer)


# ──────────────────────────────────────────────────────────────
#  Compare, in the panes (what the LTI Viewer app became)
# ──────────────────────────────────────────────────────────────

def _names(pane) -> list[str]:
    return pane.content.collection.names


def test_only_plot_panes_have_a_compare_button(app, win):
    shown = {pane.key: not pane._compare_btn.isHidden()
             for pane in win._grid.panes}
    assert shown == {"step": True, "bode": True, "rlocus": True,
                     "metrics": False}
    win._grid.panes[0].set_kind("system")
    assert win._grid.panes[0]._compare_btn.isHidden()


def test_the_compare_menu_offers_the_other_sources_and_the_snapshots(
        app, win):
    win._snapshot_bar.take("first")
    pane = win._grid.panes[0]                    # step, of T
    pane._fill_compare_menu()
    texts = [a.text() for a in pane._compare_menu.actions()
             if a.isCheckable()]
    assert "T — closed loop r→y" not in texts, "its own source is not offered"
    assert {"L — open loop", "G — plant", "S — sensitivity",
            "first"} <= set(texts)


def test_ticking_a_snapshot_in_the_compare_menu_adds_one_curve(app, win):
    win._arch.set_block("K2", ctl.tf([4], [1]))
    win._after_loop_change()
    win._snapshot_bar.take("gain 4")
    pane = win._grid.panes[0]
    assert _names(pane) == ["T"]

    pane._fill_compare_menu()
    action = next(a for a in pane._compare_menu.actions()
                  if a.text() == "gain 4")
    action.trigger()
    _settle(app, 5)
    assert _names(pane) == ["T", "gain 4"]
    assert pane.compare_keys == (("snapshot", "gain 4"),)
    _banners_clean(win)

    # Unticking takes it away again; the other panes never had it.
    pane._fill_compare_menu()
    next(a for a in pane._compare_menu.actions()
         if a.text() == "gain 4").trigger()
    assert _names(pane) == ["T"]
    assert _names(win._grid.panes[1]) == ["L"]


def test_a_snapshot_is_drawn_as_the_panes_own_system(app, win):
    """In a Bode pane of L, a snapshot is that snapshot's L, not its T."""
    win._arch.set_block("K2", ctl.tf([3], [1]))
    snapshot = win._snapshot_bar.take("k3")
    pane = win._grid.panes[1]                   # Bode, of L
    pane.tick_compare(("snapshot", "k3"))
    entry = pane.content.collection.get("k3")
    assert float(ctl.dcgain(entry.tf)) == pytest.approx(
        float(ctl.dcgain(snapshot.loop_tf())))


def test_a_deleted_snapshot_leaves_the_pane(app, win):
    win._snapshot_bar.take("gone")
    pane = win._grid.panes[0]
    pane.tick_compare(("snapshot", "gone"))
    win.snapshots.remove("gone")
    pane.refresh()
    assert _names(pane) == ["T"] and pane.compare_keys == ()


def test_another_loop_source_can_be_compared(app, win):
    pane = win._grid.panes[0]
    pane.tick_compare(("loop", "PLANT"))
    assert _names(pane) == ["T", "G"]
    # Switching the pane to that source does not draw it twice.
    from evans.ui.panes import Source

    pane.set_source(Source.PLANT)
    assert _names(pane) == ["G"]


def test_compare_ticks_ride_along_a_relayout(app, win):
    win._grid.panes[0].tick_compare(("loop", "PLANT"))
    win.set_pane_layout(2)
    assert win._grid.panes[0].compare_keys == (("loop", "PLANT"),)


def test_snapshot_compare_ticks_every_snapshot_in_every_plot_pane(app, win):
    bar = win._snapshot_bar
    win._arch.set_block("K2", ctl.tf([1], [1]))
    bar.take("P = 1")
    win._arch.set_block("K2", ctl.tf([4], [1]))
    bar.take("P = 4")
    bar.compare()
    _settle(app, 5)

    for pane in win._grid.plot_panes():
        assert pane.compare_keys == (("snapshot", "P = 1"),
                                     ("snapshot", "P = 4")), pane.key
        assert _names(pane)[1:] == ["P = 1", "P = 4"]
    assert win._grid.panes[3].compare_keys == ()       # metrics: no menu
    assert not win.side_panel.is_open, "no viewer, no panel opened"
    _banners_clean(win)


# ──────────────────────────────────────────────────────────────
#  The console commands land on the right place
# ──────────────────────────────────────────────────────────────

def test_ltiview_sets_the_first_plot_panes_compare_set(app, win):
    win.show_workspace(Workspace.CONSOLE)
    a, b = ctl.tf([1], [1, 1]), ctl.tf([2], [1, 2])
    win.open_app(AppRequest("ltiview", {"a": a, "b": b}))
    _settle(app, 5)
    assert win._stack.current is Workspace.ANALYSE
    pane = win._grid.panes[0]
    assert pane.key == "step", "the pane keeps its kind"
    assert _names(pane) == ["T", "a", "b"]

    # A second call names the new set; the earlier systems stay on offer.
    win.open_app(AppRequest("ltiview", {"c": ctl.tf([3], [1, 3])}))
    assert _names(pane) == ["T", "c"]
    offered = {o.label for o in win._grid.panes[1].compare_options()}
    assert {"a", "b", "c"} <= offered


def test_ltiview_with_nothing_named_compares_the_loop(app, win):
    win.open_app(AppRequest("ltiview", {}))
    assert _names(win._grid.panes[0]) == ["T", "G", "L"]


def test_ltiview_with_no_plot_pane_makes_pane_one_a_step(app, win):
    win._grid.set_layout_size(1, ("system",), (None,))
    win.open_app(AppRequest("ltiview", {"a": ctl.tf([1], [1, 1])}))
    _settle(app, 5)
    pane = win._grid.panes[0]
    assert pane.key == "step"
    assert _names(pane) == ["T", "a"]


def test_sisotool_opens_design_on_compensator_with_the_plant(app, win):
    win.show_workspace(Workspace.CONSOLE)
    win.open_app(AppRequest("sisotool", {"plant": LOCUS_PLANT}))
    _settle(app, 10)
    side = win.side_panel_of(Workspace.ANALYSE)
    assert win._stack.current is Workspace.ANALYSE
    assert side.is_open and side.current == "design"
    assert win._design.mode == "compensator"
    assert win._design.designer.view == "compensator"
    assert np.allclose(win._arch.block_tf("G").den[0][0], [1, 3, 2, 0])
    assert win._loop_undo.undoText() == "sisotool"
    _banners_clean(win)


def test_pidtuner_opens_design_on_pid_with_that_kind(app, win):
    before = session_dict(win._arch)
    win.open_app(AppRequest("pidtuner", {}, {"kind": "PID"}))
    _settle(app, 10)
    side = win.side_panel_of(Workspace.ANALYSE)
    assert side.is_open and side.current == "design"
    assert win._design.mode == "pid"
    assert win._design.tuner.kind.value == "PID"
    assert session_dict(win._arch) == before, \
        "choosing the kind is not a change to the loop"


# ──────────────────────────────────────────────────────────────
#  The designer (Gain and Compensator)
# ──────────────────────────────────────────────────────────────

def test_gain_and_compensator_are_two_views_of_one_designer(app, win):
    design = win._design
    win.show_design("gain")
    gain_view = design._stack.currentWidget()
    win.show_design("compensator")
    assert design._stack.currentWidget() is gain_view is design.designer
    assert design.designer._zeros_edit.isVisible()
    assert not design.designer._gain_spin.isVisible()
    win.show_design("pid")
    assert design._stack.currentWidget() is design.tuner


def test_the_designer_keeps_its_locus_inside_the_panel(app, win):
    designer = _designer(app, win)
    panel = designer._locus_widget
    assert panel.height() >= LOCUS_HEIGHT == 220
    assert panel.getPlotItem().boundingRect().width() <= \
        panel.sceneRect().width() + 1, "the locus is wider than its panel"


def test_a_long_title_cannot_stretch_a_plot_off_its_panel(app):
    """
    A pyqtgraph title is a ``LabelItem`` whose *minimum* width is its text
    width, so a long title lays the whole ``PlotItem`` out wider than the
    scene and pushes every curve off the right-hand edge. The panel then looks
    blank while every value in it is correct and nothing reports an error —
    which is exactly how it was found, in the designer's root locus.
    """
    from evans.ui.plots import make_plot

    widget = make_plot("Root locus", "Re", "Im")
    widget.resize(434, 470)
    widget.show()
    _settle(app, 10)

    plot = widget.getPlotItem()
    plot.setTitle("Root locus — crosses the imaginary axis at "
                  "K = 6.0001, ω = 1.41421356")
    _settle(app, 10)
    assert plot.boundingRect().width() <= widget.sceneRect().width() + 1
    widget.hide()


def test_the_marginal_gain_is_reported_in_the_readout(app, win):
    """It used to be the plot title, which is what caused the stretch."""
    designer = _designer(app, win)
    designer.set_plant(LOCUS_PLANT)
    _settle(app, 5)
    assert "imaginary axis" in designer._readout.text()


def test_the_designer_builds_its_locus_and_target(app, win):
    designer = _designer(app, win)
    _banners_clean(designer)
    assert designer._summary is not None
    assert designer._target is not None, "nothing to drag"
    assert designer._readout.text()


def test_picking_a_point_moves_the_gain_and_the_readout(app, win):
    designer = _designer(app, win)
    designer.set_plant(LOCUS_PLANT)
    _settle(app, 3)

    target_pole = max(closed_loop_poles(LOCUS_PLANT, 2.0),
                      key=lambda p: p.imag)
    designer.pick_point(target_pole)
    _settle(app, 3)

    _banners_clean(designer)
    assert designer.compensator.gain == pytest.approx(2.0, rel=1e-2)
    assert designer._gain_spin.value() == pytest.approx(2.0, rel=1e-2)
    assert "K = 2" in designer._readout.text()


def test_the_damping_button_reaches_the_textbook_gain_and_applies(app, win):
    win.change_loop("plant", lambda: win._arch.set_block("G", LOCUS_PLANT))
    designer = _designer(app, win)
    designer._zeta_spin.setValue(0.5)
    designer._set_gain_for_damping()
    _settle(app, 3)
    _banners_clean(designer)
    assert designer.compensator.gain == pytest.approx(28 / 27, rel=1e-4)
    assert _k2_gain(win) == pytest.approx(28 / 27, rel=1e-4)
    assert win._loop_undo.undoText() == "Design: gain"


def test_an_unreachable_target_shows_a_banner_rather_than_crashing(app, win):
    designer = _designer(app, win)
    designer.set_plant(ctl.tf([1], [1, 1]))     # one real branch, no ζ < 1
    designer._zeta_spin.setValue(0.5)
    designer._set_gain_for_damping()
    _settle(app, 3)
    assert designer._error_banner.has_error
    assert "lead section" in designer._error_banner.message


def test_a_typo_in_the_compensator_lands_in_the_banner(app, win):
    """
    Parsing happens inside the guarded rebuild, not in the line edit's own
    slot — otherwise the exception escapes from a Qt signal and takes the app
    with it. Nothing is applied to the loop.
    """
    designer = _designer(app, win, "compensator")
    depth = win._loop_undo.count()
    designer._zeros_edit.setText("-1, banana")
    designer._on_roots_edited()
    _settle(app, 3)
    assert designer._error_banner.has_error
    assert "is not a number" in designer._error_banner.message
    assert win._loop_undo.count() == depth


def test_an_unpaired_complex_root_is_refused(app, win):
    designer = _designer(app, win, "compensator")
    designer._poles_edit.setText("-1+2j")
    designer._on_roots_edited()
    _settle(app, 3)
    assert designer._error_banner.has_error
    assert "conjugate" in designer._error_banner.message
    assert _k2_gain(win) == pytest.approx(1.0)


def test_adding_a_lead_applies_it_to_the_loop(app, win):
    designer = _designer(app, win, "compensator")
    designer._add_lead()
    _settle(app, 3)
    _banners_clean(designer)
    assert designer.compensator.zeros == [complex(-1.0, 0.0)]
    assert designer.compensator.poles == [complex(-10.0, 0.0)]
    K2 = win._arch.block_tf("K2")
    assert np.allclose(np.roots(K2.num[0][0]), [-1.0])
    assert np.allclose(np.roots(K2.den[0][0]), [-10.0])
    assert win._loop_undo.undoText() == "Design: compensator"


def test_a_typed_gain_sets_k2_at_once(app, win):
    designer = _designer(app, win)
    designer._gain_spin.setValue(3.5)
    _settle(app, 5)
    assert _k2_gain(win) == pytest.approx(3.5, rel=1e-6)


def test_a_gain_slider_drag_updates_the_panes_and_is_one_undo_step(
        app, win):
    designer = _designer(app, win)
    slider = designer._gain_slider
    step_pane = win._grid.panes[0]
    depth = win._loop_undo.count()

    slider.setSliderDown(True)
    for ticks in range(10, 110, 10):           # ten moves, K = 10^0.1 … 10
        slider.setValue(ticks)
        _wait(app, APPLY_INTERVAL_MS // 2)
    _wait(app, 2 * APPLY_INTERVAL_MS)
    assert _k2_gain(win) > 1.0, "nothing was applied during the drag"
    slider.setSliderDown(False)                 # releases: one last apply
    _settle(app, 5)

    assert _k2_gain(win) == pytest.approx(10.0, rel=1e-6)
    assert win._loop_undo.count() == depth + 1, "one drag, one undo step"
    T = win._arch.get_closed_loop_tf("r", "y")
    drawn = step_pane.content.collection.get("T").tf
    assert float(ctl.dcgain(drawn)) == pytest.approx(float(ctl.dcgain(T)))

    # A second drag is a step of its own.
    slider.setSliderDown(True)
    slider.setValue(50)
    slider.setSliderDown(False)
    _settle(app, 5)
    assert win._loop_undo.count() == depth + 2


def test_reset_restores_the_k2_from_when_the_tab_was_shown(app, win):
    win.change_loop("K2 = 2", lambda: win._arch.set_block(
        "K2", ctl.tf([2], [1])))
    designer = _designer(app, win)
    designer._gain_spin.setValue(7.0)
    _settle(app, 5)
    assert _k2_gain(win) == pytest.approx(7.0)

    win._design.reset()
    _settle(app, 5)
    assert _k2_gain(win) == pytest.approx(2.0)
    assert designer._gain_spin.value() == pytest.approx(2.0), \
        "the widgets follow the reset"
    assert win._loop_undo.undoText() == "Design: reset"


def test_an_undo_moves_the_widgets_back_without_reapplying(app, win):
    designer = _designer(app, win)
    designer._gain_spin.setValue(5.0)
    _settle(app, 5)
    assert _k2_gain(win) == pytest.approx(5.0)
    count = win._loop_undo.count()

    win._act_undo.trigger()                     # Edit > Undo
    _settle(app, 5)
    assert _k2_gain(win) == pytest.approx(1.0)
    assert designer._gain_spin.value() == pytest.approx(1.0)
    assert designer.compensator.gain == pytest.approx(1.0)
    assert win._loop_undo.count() == count, "the re-read pushed a step"
    assert win._loop_undo.canRedo()


def test_its_own_apply_does_not_reread_the_loop(app, win):
    """The `_applying` guard: a write from the tab is not read back into it."""
    design = win.show_design("gain")
    _settle(app, 5)
    calls = []
    original = design.designer.set_plant
    design.designer.set_plant = lambda *a, **k: calls.append(a) or \
        original(*a, **k)
    try:
        design.designer._gain_spin.setValue(2.5)
        _settle(app, 5)
    finally:
        design.designer.set_plant = original
    assert not calls
    assert _k2_gain(win) == pytest.approx(2.5)


def test_a_preset_changes_the_plant_under_the_designer(app, win):
    designer = _designer(app, win)
    win.change_loop("plant", lambda: win._arch.set_block("G", LOCUS_PLANT))
    _settle(app, 5)
    assert np.allclose(designer._plant.den[0][0], [1, 3, 2, 0])


# ──────────────────────────────────────────────────────────────
#  PID
# ──────────────────────────────────────────────────────────────

def test_the_tuner_builds_and_tunes(app, win):
    tuner = _tuner(app, win)
    _banners_clean(tuner)
    assert tuner.result is not None and tuner.result.feasible
    assert "PM" in tuner._readout.text()


def test_the_sliders_change_the_design(app, win):
    """
    The plant is pinned rather than inherited from the window: the slider
    range that is *feasible* depends on how much phase the plant has to spare,
    and a test that silently sampled an infeasible target would be asserting
    on a nan.
    """
    tuner = _tuner(app, win)
    tuner.set_plant(ctl.tf([1], [1, 3, 3, 1]))
    tuner._kind_combo.setCurrentText("PID")
    tuner._speed.setValue(-20)
    _settle(app, 3)
    slow = tuner.result
    tuner._speed.setValue(20)
    _settle(app, 3)
    fast = tuner.result
    _banners_clean(tuner)
    assert slow.feasible and fast.feasible
    assert fast.achieved_wc > slow.achieved_wc
    assert fast.response_time < slow.response_time


def test_the_slider_labels_state_what_they_do(app, win):
    """The sliders are only honest if they say which target they set."""
    tuner = _tuner(app, win)
    assert "rad/s" in tuner._speed_label.text()
    assert "phase margin" in tuner._transient_label.text()


def test_an_impossible_target_explains_itself_and_leaves_k2(app, win):
    win.change_loop("plant", lambda: win._arch.set_block(
        "G", ctl.tf([1], [1, 3, 3, 1])))
    tuner = _tuner(app, win)
    tuner._kind_combo.setCurrentText("PI")
    _settle(app, 3)
    applied = session_dict(win._arch)
    tuner._speed.setValue(60)                 # far above the plant's phase
    _settle(app, 3)
    assert not tuner.result.feasible
    assert not tuner._error_banner.has_error, \
        "an impossible target is an answer, not an error"
    assert "phase" in tuner._readout.text()
    assert session_dict(win._arch) == applied, "nothing to apply"


def test_a_tuner_change_reaches_the_architecture(app, win):
    win.change_loop("plant", lambda: win._arch.set_block(
        "G", ctl.tf([1], [1, 3, 3, 1])))
    tuner = _tuner(app, win)
    tuner.set_kind("PI")                    # quietly: not a change to apply
    assert win._loop_undo.undoText() == "plant"
    tuner._kind_combo.setCurrentText("PID")
    _settle(app, 3)
    expected = np.atleast_1d(tuner.result.C.num[0][0])
    assert len(expected) == 3
    assert np.allclose(np.atleast_1d(win._arch.block_tf("K2").num[0][0]),
                       expected)
    assert win._loop_undo.undoText() == "Design: PID"


def test_the_tuner_tunes_in_the_real_loop(app, win):
    """K₁ and H come from the architecture, not a unity-feedback guess."""
    def mutate():
        win._arch.set_block("K1", ctl.tf([3], [1]))
        win._arch.set_block("H", ctl.tf([1], [0.2, 1]))
    win.change_loop("loop", mutate)
    tuner = _tuner(app, win)
    assert float(ctl.dcgain(tuner._feedforward)) == pytest.approx(3.0)
    assert np.allclose(tuner._sensor.den[0][0], [0.2, 1])


# ──────────────────────────────────────────────────────────────
#  Snapshots, across panes
# ──────────────────────────────────────────────────────────────

def test_a_snapshot_taken_on_one_pane_restores_from_another(app, win):
    bar = win._snapshot_bar
    win._arch.set_block("K2", ctl.tf([2], [1]))
    bar.take("gain 2")

    win._grid.panes[0].set_kind("frequency")
    win._arch.set_block("K2", ctl.tf([9], [1]))
    _settle(app, 3)

    bar._combo.setCurrentText("gain 2")
    bar.restore()
    _settle(app, 3)
    assert _k2_gain(win) == pytest.approx(2.0)


def test_restoring_refreshes_the_visible_pane(app, win):
    """A restore that leaves a pane showing the old design is worse than none."""
    win._grid.panes[0].set_kind("system")
    win._arch.set_block("G", ctl.tf([1], [1, 1]))
    win._snapshot_bar.take("first order")
    win._arch.set_block("G", ctl.tf([1], [1, 5, 6]))
    _settle(app, 3)

    win._snapshot_bar._combo.setCurrentText("first order")
    win._snapshot_bar.restore()
    _settle(app, 5)
    _banners_clean(win)
    assert len(np.atleast_1d(ctl.poles(win._arch.block_tf("G")))) == 1


def test_a_new_session_rebinds_the_snapshot_bar(app, win):
    """
    ``_new_session`` keeps the architecture object. Anything holding another
    one goes on snapshotting a plant that is no longer on screen.
    """
    win._new_session()
    _settle(app, 5)
    assert win._snapshot_bar._arch is win._arch
    assert win._design._arch is win._arch
    win._arch.set_block("K2", ctl.tf([7], [1]))
    snapshot = win._snapshot_bar.take("after new")
    assert float(ctl.dcgain(snapshot.tf("K2"))) == pytest.approx(7.0)


# ──────────────────────────────────────────────────────────────
#  The apps are gone
# ──────────────────────────────────────────────────────────────

def test_there_is_no_apps_menu_and_no_app_dock(app, win):
    from PySide6.QtWidgets import QDockWidget

    titles = [a.text().replace("&", "") for a in win.menuBar().actions()]
    assert "Apps" not in titles
    assert not win.findChildren(QDockWidget)
    for gone in ("_apps", "_app_docks", "_APP_DOCKS", "_show",
                 "_open_lti_viewer", "_open_designer", "_open_pid_tuner",
                 "_default_viewer_systems"):
        assert not hasattr(win, gone), gone
    shortcuts = {a.shortcut().toString() for a in win.findChildren(
        type(win._act_undo)) if not a.shortcut().isEmpty()}
    assert not shortcuts & {"Ctrl+Shift+L", "Ctrl+Shift+D", "Ctrl+Shift+T"}


def test_the_design_tab_leaves_the_minimum_size_alone(app, win):
    side = win.side_panel_of(Workspace.ANALYSE)
    side.set_current("loop")
    side.set_open(True)
    _settle(app, 5)
    with_loop = win.minimumSizeHint()
    for mode in ("gain", "compensator", "pid"):
        win.show_design(mode)
        _settle(app, 5)
        hint = win.minimumSizeHint()
        assert hint.width() <= with_loop.width(), (mode, hint, with_loop)
        assert hint.height() <= with_loop.height(), (mode, hint, with_loop)


# ──────────────────────────────────────────────────────────────
#  R6b: the Design and Loop tabs use the panel's height; Design button
# ──────────────────────────────────────────────────────────────

def _bottom_in(widget, ancestor) -> int:
    return widget.mapTo(ancestor, widget.rect().bottomLeft()).y() + 1


@pytest.mark.parametrize("mode", ["gain", "compensator", "pid"])
def test_the_design_page_has_no_empty_space_below_its_content(app, win, mode):
    design = win.show_design(mode)
    _settle(app, 10)
    if mode == "pid":
        plot, last = design.tuner._viewer, design.tuner._readout
        page = design.tuner
    else:
        plot, last = design.designer._locus_widget, design.designer._readout
        page = design.designer
    # The plot took the free height: more than its minimum.
    assert plot.height() > max(LOCUS_HEIGHT, PLOT_MIN_HEIGHT), mode
    # The last of the page's content reaches the page's bottom edge.
    assert _bottom_in(last if mode != "pid" else design.tuner._readout, page)         >= page.height() - 60, mode
    # And the Reset row is at the bottom of the whole tab.
    assert _bottom_in(design._reset_btn, design) >= design.height() - 2
    assert page.height() + design._reset_btn.height() <= design.height() + 40


def test_the_pid_page_has_no_stretch_below_its_last_button(app, win):
    design = win.show_design("pid")
    _settle(app, 10)
    tuner = design.tuner
    reset = [b for b in tuner.findChildren(type(design._reset_btn))
             if b.text() == "Reset sliders"][0]
    assert _bottom_in(reset, tuner) >= tuner.height() - 1


def test_the_plot_keeps_its_minimum_when_the_panel_is_short(app, win):
    design = win.show_design("gain")
    _settle(app, 5)
    assert design.designer._locus_widget.minimumHeight() == LOCUS_HEIGHT
    win.show_design("pid")
    assert design.tuner._viewer.minimumHeight() == PLOT_MIN_HEIGHT


def test_the_loop_tab_gives_the_diagram_the_upper_45_percent(app, win):
    win.show_loop_editor()
    _settle(app, 10)
    diagram, editor = win._diagram, win._editor
    assert diagram.minimumHeight() == 150
    assert diagram.maximumHeight() > 260              # no cap
    holder = win.side_panel_of(Workspace.ANALYSE).holder("loop")
    spacing = holder.layout().spacing()
    m = holder.layout().contentsMargins()
    free = holder.height() - m.top() - m.bottom() - editor.height()
    free -= 2 * spacing
    # About 45 % of what the editor leaves free (150 px at least).
    expected = max(150, round(0.45 * free))
    assert abs(diagram.height() - expected) <= 12, (diagram.height(), expected)
    # The editor directly below the diagram, at its natural height ...
    assert editor.y() - (diagram.y() + diagram.height()) <= spacing + 1
    assert editor.height() <= editor.sizeHint().height() + 2
    # ... and the rest of the tab is under the editor.
    assert _bottom_in(editor, holder) < holder.height() - 2 * 8
    assert holder.height() - _bottom_in(editor, holder) > 40


def test_the_design_button_opens_the_panel_on_design_and_closes_it(app, win):
    side = win.side_panel_of(Workspace.ANALYSE)
    button = win._context._design_btn
    assert button.text() == "Design" and button.accessibleName() == "Design"
    assert button.x() > win._context._edit_btn.x()    # beside Edit loop
    assert not side.is_open
    QTest.mouseClick(button, Qt.LeftButton)
    _settle(app, 5)
    assert side.is_open and side.current == "design"
    QTest.mouseClick(button, Qt.LeftButton)
    _settle(app, 5)
    assert not side.is_open


def test_the_design_button_switches_from_another_tab(app, win):
    side = win.side_panel_of(Workspace.ANALYSE)
    win.show_loop_editor()
    assert side.current == "loop"
    win._context._design_btn.click()
    _settle(app, 5)
    assert side.is_open and side.current == "design"


def test_edit_loop_closes_the_panel_when_already_on_loop(app, win):
    side = win.side_panel_of(Workspace.ANALYSE)
    win._context._edit_btn.click()
    assert side.is_open and side.current == "loop"
    win._context._edit_btn.click()
    assert not side.is_open


# ──────────────────────────────────────────────────────────────
#  R6b: the PID page's own plot
# ──────────────────────────────────────────────────────────────

def test_the_pid_plot_defaults_to_the_closed_loop_step(app, win):
    tuner = _tuner(app, win)
    _wait(app, APPLY_INTERVAL_MS * 2)
    assert tuner.plot_view is ResponseKind.STEP
    assert [b.text() for b in tuner._plot_buttons.values()] ==         ["Step", "Bode", "Nichols"]
    assert tuner._plot_buttons[ResponseKind.STEP].isChecked()
    names = [e.name for e in tuner._viewer.collection]
    assert names == ["Closed loop"]
    assert tuner._viewer._kind is ResponseKind.STEP
    _banners_clean(tuner)


def test_the_pid_plot_switches_between_step_bode_and_nichols(app, win):
    tuner = _tuner(app, win)
    for view in PLOT_VIEWS:
        tuner._plot_buttons[view].click()
        _settle(app, 5)
        assert tuner.plot_view is view
        assert tuner._viewer._kind is view
        assert tuner._plot_buttons[view].isChecked()
        _banners_clean(tuner)
    assert [e.name for e in tuner._viewer.collection] == ["Open loop"]


def test_the_pid_plot_follows_a_slider(app, win):
    tuner = _tuner(app, win)
    _wait(app, APPLY_INTERVAL_MS * 2)
    shown = lambda: list(tuner._viewer.collection)[0].system   # noqa: E731
    before = shown()
    assert before is tuner.result.T
    tuner._speed.setValue(4)                    # a feasible, faster target
    assert tuner.result.feasible
    _wait(app, APPLY_INTERVAL_MS * 3)
    assert shown() is tuner.result.T and shown() is not before


def test_the_pid_plot_is_throttled_like_the_rest_of_the_tab(app, win):
    tuner = _tuner(app, win)
    _wait(app, APPLY_INTERVAL_MS * 2)
    draws = []
    real = tuner._viewer.refresh
    tuner._viewer.refresh = lambda *a: (draws.append(1), real(*a))[1]
    try:
        for ticks in range(-8, 4):
            tuner._speed.setValue(ticks)        # twelve moves, back to back
        assert len(draws) <= 1
        _wait(app, APPLY_INTERVAL_MS * 3)
        assert 1 <= len(draws) <= 3
    finally:
        del tuner._viewer.refresh
