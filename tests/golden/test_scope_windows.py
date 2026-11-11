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


def test_hint_mentions_the_scope_double_click(tab):
    assert "Scope block for its plot" in tab._hint.text()


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
