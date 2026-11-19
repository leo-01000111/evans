"""
A Scope block's own window, and the global scope folded behind a button.

Double-clicking a Scope block opens a window with only the signals wired into
it; the same block raises the same window; a run redraws the open ones and
another model closes them. Every other block keeps double-click for its
parameters. The pop-out is the global scope's widget, so copy and export
work there too.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="Qt not available")

from PySide6.QtWidgets import QApplication  # noqa: E402

from evans.sim import SimModel, simulate  # noqa: E402
from evans.ui import persist  # noqa: E402
from evans.ui.sim import scope_window  # noqa: E402
from evans.ui.sim.canvas import SimCanvas  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def two_scopes() -> SimModel:
    """A loop with two Scope blocks watching different signals."""
    m = SimModel("two scopes")
    m.add("Step", "r", x=0, y=0, step_time=0.0)
    m.add("Sum", "e", x=150, y=0, signs="+-")
    m.add("Gain", "K", x=300, y=0, gain=4.0)
    m.add("TransferFcn", "G", x=450, y=0, num="1", den="1, 1")
    m.add("Scope", "out", x=600, y=0, title="Output", n_inputs=2)
    m.add("Scope", "effort", x=450, y=150, title="Effort")
    m.add("Scope", "idle", x=600, y=150, title="Idle")
    m.connect("r", "e.in1")
    m.connect("e", "K")
    m.connect("K", "G")
    m.connect("G", "e.in2")
    m.connect("r", "out.in1")
    m.connect("G", "out.in2")
    m.connect("K", "effort")
    return m


@pytest.fixture
def tab(app):
    from evans.ui.sim.sim_tab import SimTab
    widget = SimTab()
    widget._canvas.set_model(two_scopes())
    yield widget
    widget.close_scope_windows()
    widget.shutdown()
    widget.deleteLater()


def _run(tab, **kw):
    """A run, as the Model tab's own finishing a simulation shows it."""
    result = simulate(tab._canvas.root_model(), t_end=kw.get("t_end", 2.0),
                      n_points=101)
    tab._on_finished(result)
    return result


def _shown(window) -> list[str]:
    return list(window.scope._checks)


def test_double_click_opens_a_window_with_only_that_blocks_signals(tab):
    _run(tab)
    tab._canvas._edit_params("out")          # what a double-click calls
    windows = tab.scope_windows()
    assert list(windows) == ["out"]
    window = windows["out"]
    assert window.isVisible()
    assert _shown(window) == ["r.out", "G.out"]
    assert all(c.isChecked() for c in window.scope._checks.values())
    assert "Output" in window.windowTitle()
    assert "two scopes" in window.windowTitle()
    # The global scope still offers every logged signal.
    assert set(tab._scope._checks) == set(tab._scope.result.signals)

    tab._canvas._edit_params("effort")
    assert set(tab.scope_windows()) == {"out", "effort"}
    assert _shown(tab.scope_windows()["effort"]) == ["K.out"]


def test_a_second_double_click_raises_the_same_window(tab):
    _run(tab)
    first = tab.open_scope_window("out")
    first.hide()
    tab._canvas._edit_params("out")
    assert tab.scope_windows()["out"] is first
    assert first.isVisible()
    assert len(tab.scope_windows()) == 1


def test_a_closed_window_opens_anew(tab, app):
    _run(tab)
    first = tab.open_scope_window("out")
    first.close()
    assert tab.scope_windows() == {}
    again = tab.open_scope_window("out")
    assert again is not first and again.isVisible()


def test_a_rerun_updates_an_open_window(tab):
    first = _run(tab)
    window = tab.open_scope_window("out")
    assert window.scope.result is first
    tab._canvas.model.block("K").set_param("gain", 9.0)
    second = _run(tab)
    assert window.scope.result is second
    assert window.scope.history[0] is first


def test_window_says_so_before_a_run_or_with_nothing_wired(tab):
    window = tab.open_scope_window("out")
    assert window.message() == scope_window.NOT_RUN
    _run(tab)
    assert window.message() == ""
    idle = tab.open_scope_window("idle")
    assert idle.message() == scope_window.NOTHING_WIRED


def test_window_opened_after_several_runs_can_compare(tab):
    first = _run(tab)
    _run(tab)
    window = tab.open_scope_window("out")
    assert window.scope.history == [first]


def test_a_scope_inside_a_subsystem_is_keyed_by_its_path(app):
    from evans.ui.sim.sim_tab import SimTab
    inner = SimModel("inner")
    inner.add("Inport", "u_in")
    inner.add("Gain", "k", gain=2.0)
    inner.add("Scope", "watch", title="Inside")
    inner.add("Outport", "y_out")
    inner.connect("u_in", "k")
    inner.connect("k", "y_out")
    inner.connect("k", "watch")
    outer = SimModel("outer")
    outer.add("Step", "r", step_time=0.0)
    outer.add("Subsystem", "S", name="S").set_inner(inner)
    outer.add("Terminator", "t")
    outer.connect("r", "S")
    outer.connect("S", "t")
    tab = SimTab()
    try:
        tab._canvas.set_model(outer)
        _run(tab)
        tab._canvas.descend("S")
        tab._canvas._edit_params("watch")
        window = tab.scope_windows()["S/watch"]
        assert _shown(window) == ["S/k.out"]
        assert "Inside" in window.windowTitle()
    finally:
        tab.close_scope_windows()
        tab.shutdown()
        tab.deleteLater()


def test_loading_another_model_closes_the_windows(tab, tmp_path):
    _run(tab)
    out = tab.open_scope_window("out")
    effort = tab.open_scope_window("effort")
    path = tmp_path / "other.evx"
    two_scopes().save(path)
    tab.load_model(path)
    assert tab.scope_windows() == {}
    assert not out.isVisible() and not effort.isVisible()


def test_global_scope_collapses_expands_and_persists(app):
    from evans.ui.sim.sim_tab import SimTab
    persist.settings().remove(persist.GLOBAL_SCOPE_KEY)
    tab = SimTab()
    try:
        assert not tab.global_scope_visible()          # folded by default
        assert tab._scope.isHidden()
        assert tab._global_button.text() == "Show global scope"

        tab._global_button.click()
        assert tab.global_scope_visible()
        assert not tab._scope.isHidden()
        assert tab._global_button.text() == "Hide global scope"
        assert persist.global_scope_open()
    finally:
        tab.deleteLater()

    reopened = SimTab()
    try:
        assert reopened.global_scope_visible()
        reopened.set_global_scope_visible(False)
        assert reopened._scope.isHidden()
        assert not persist.global_scope_open()
    finally:
        reopened.deleteLater()
        persist.settings().remove(persist.GLOBAL_SCOPE_KEY)


def test_double_click_on_another_block_still_opens_parameters(app,
                                                              monkeypatch):
    from evans.ui.sim import params
    opened = []

    class FakeDialog:
        changes = {}

        def __init__(self, block, parent=None):
            opened.append(block.block_id)

        def exec(self):
            return False

    monkeypatch.setattr(params, "ParamDialog", FakeDialog)
    view = SimCanvas(two_scopes())
    requested = []
    view.scope_requested.connect(requested.append)
    try:
        view._edit_params("K")
        assert opened == ["K"] and requested == []
        view._edit_params("out")
        assert opened == ["K"] and requested == ["out"]
    finally:
        view.deleteLater()


def test_global_scope_toggle_mentions_the_scope_double_click(tab):
    assert "Double-click a Scope block" in tab._global_button.toolTip()


def test_copy_and_export_from_a_pop_out(tab, tmp_path):
    _run(tab)
    window = tab.open_scope_window("out")
    window.resize(600, 400)
    QApplication.clipboard().clear()
    window.scope._copy_action.trigger()
    mime = QApplication.clipboard().mimeData()
    assert mime.hasImage()
    assert mime.text().split("\n")[0].split("\t") == ["t", "r.out", "G.out"]

    png = tmp_path / "out.png"
    window.scope.export_image(png, width=3.0, height=2.0, dpi=50)
    assert png.read_bytes()[:4] == b"\x89PNG"
    spec = window.scope.figure_spec()
    assert spec.title == "Output"

    csv = tmp_path / "out.csv"
    window.scope.export(csv)
    header = csv.read_text().splitlines()[0]
    assert "r.out" in header and "G.out" in header
    assert "K.out" not in header                 # only this block's signals


def test_pop_out_has_no_xy_view_choice(tab):
    _run(tab)
    window = tab.open_scope_window("out")
    assert window.scope._view.isHidden()


# ──────────────────────────────────────────────────────────────
#  Dock or window (R6)
# ──────────────────────────────────────────────────────────────

@pytest.fixture
def prefers_panel():
    persist.set_scope_opens_in("panel")
    yield
    persist.settings().remove(persist.SCOPE_OPENS_IN_KEY)


def test_a_scope_window_has_a_dock_button(tab):
    window = tab.open_scope_window("out")
    button = window.view.dock_button
    assert button.text() == "Dock"
    assert button.accessibleName() == "Dock scope"


def test_the_dock_button_shares_the_export_row(tab):
    _run(tab)
    window = tab.open_scope_window("out")
    window.show()
    QApplication.processEvents()
    view = window.view
    export = view.scope._export
    dock = view.dock_button
    assert view.message() == ""
    assert dock.parentWidget() is export.parentWidget() or         view.scope.isAncestorOf(dock)
    top = lambda w: w.mapTo(view, w.rect().topLeft()).y()   # noqa: E731
    centre = lambda w: top(w) + w.height() // 2             # noqa: E731
    assert abs(centre(dock) - centre(export)) <= 3          # one row
    assert dock.mapTo(view, dock.rect().topLeft()).x()         >= export.mapTo(view, export.rect().topLeft()).x() + export.width()
    # No row of its own above the plot: the toolbar is the first thing.
    assert top(export) < 40
    window.close()


def test_the_dock_button_is_reachable_before_a_run_too(tab):
    window = tab.open_scope_window("out")
    window.show()
    QApplication.processEvents()
    view = window.view
    assert view.message() != ""
    assert view.dock_button.isVisible()
    _run(tab)
    QApplication.processEvents()          # the layout shows what it moved
    assert view.message() == ""
    assert view.dock_button.isVisible()
    window.close()


def test_dock_moves_the_same_widget_into_the_side_panel(tab):
    _run(tab)
    window = tab.open_scope_window("out")
    scope = window.scope
    window.scope._compare.setChecked(True)
    untick = next(iter(scope._checks))
    scope._checks[untick].setChecked(False)

    view = tab.dock_scope("out")
    assert tab.scope_windows() == {}
    assert not window.isVisible()
    assert tab.docked_scopes() == {"out": view}
    assert view.scope is scope                       # one widget, moved
    assert tab.side_panel.keys == ("properties", "scope:out")
    assert tab.side_panel.title("scope:out") == "Scope: Output"
    assert tab.side_panel.current == "scope:out"
    assert tab.side_panel.is_open
    assert view.dock_button.text() == "Undock"
    assert view.dock_button.accessibleName() == "Undock scope"
    assert scope._compare.isChecked()
    assert not scope._checks[untick].isChecked()
    assert view.parentWidget() is tab.side_panel.holder("scope:out")


def test_a_docked_scope_goes_before_cedric(tab):
    tab.side_panel.add_tab("cedric", "Cedric")
    tab.dock_scope("out")
    tab.dock_scope("effort")
    assert tab.side_panel.keys == ("properties", "scope:out", "scope:effort",
                                   "cedric")


def test_undock_moves_it_back_to_a_window(tab):
    _run(tab)
    view = tab.dock_scope("out")
    scope = view.scope
    scope._compare.setChecked(True)
    window = tab.undock_scope("out")
    assert tab.docked_scopes() == {}
    assert tab.side_panel.keys == ("properties",)
    assert tab.scope_windows() == {"out": window}
    assert window.isVisible()
    assert window.scope is scope and scope._compare.isChecked()
    assert window.view.dock_button.text() == "Dock"
    assert "Output" in window.windowTitle()


def test_the_buttons_do_it(tab):
    _run(tab)
    tab.open_scope_window("out").view.dock_button.click()
    assert list(tab.docked_scopes()) == ["out"]
    assert tab.scope_windows() == {}
    tab.docked_scopes()["out"].dock_button.click()
    assert tab.docked_scopes() == {}
    assert list(tab.scope_windows()) == ["out"]


def test_default_preference_is_a_window(tab):
    persist.settings().remove(persist.SCOPE_OPENS_IN_KEY)
    tab._canvas._edit_params("out")
    assert list(tab.scope_windows()) == ["out"]
    assert tab.docked_scopes() == {}


def test_preference_panel_opens_a_double_click_in_the_side_panel(
        tab, prefers_panel):
    _run(tab)
    tab._canvas._edit_params("out")                 # what a double-click calls
    assert tab.scope_windows() == {}
    view = tab.docked_scopes()["out"]
    assert view.message() == ""
    assert tab.side_panel.current == "scope:out"
    tab.side_panel.set_current("properties")
    tab._canvas._edit_params("out")                 # raises the same tab
    assert tab.docked_scopes()["out"] is view
    assert tab.side_panel.current == "scope:out"
    assert tab.side_panel.keys.count("scope:out") == 1


def test_a_scope_already_in_a_window_stays_there_under_the_panel_preference(
        tab, prefers_panel):
    persist.set_scope_opens_in("window")
    window = tab.open_scope_window("out")
    persist.set_scope_opens_in("panel")
    tab._canvas._edit_params("out")
    assert tab.scope_windows() == {"out": window}
    assert tab.docked_scopes() == {}


def test_opening_a_docked_scope_as_a_window_undocks_it(tab):
    tab.dock_scope("out")
    window = tab.open_scope_window("out")
    assert tab.docked_scopes() == {}
    assert tab.scope_windows() == {"out": window}


def test_a_rerun_redraws_docked_and_windowed_scopes(tab):
    first = _run(tab)
    docked = tab.dock_scope("out")
    window = tab.open_scope_window("effort")
    assert docked.scope.result is first
    assert window.scope.result is first
    second = _run(tab)
    assert docked.scope.result is second
    assert window.scope.result is second
    assert docked.scope.history[0] is first


def test_a_docked_scope_opened_before_a_run_says_so_then_draws(tab):
    view = tab.dock_scope("out")
    assert view.message() == scope_window.NOT_RUN
    _run(tab)
    assert view.message() == ""


def test_loading_another_model_closes_docked_scopes_too(tab, tmp_path):
    _run(tab)
    docked = tab.dock_scope("out")
    window = tab.open_scope_window("effort")
    path = tmp_path / "other.evx"
    two_scopes().save(path)
    tab.load_model(path)
    assert tab.docked_scopes() == {} and tab.scope_windows() == {}
    assert tab.side_panel.keys == ("properties",)
    assert not window.isVisible()
    assert docked.parent() is None


def test_a_tab_follows_the_blocks_title(tab):
    _run(tab)
    tab._canvas.model.block("out").set_param("title", "Renamed")
    view = tab.dock_scope("out")
    _run(tab)
    assert tab.side_panel.title("scope:out") == "Scope: Renamed"
    assert view.title == "Renamed"
