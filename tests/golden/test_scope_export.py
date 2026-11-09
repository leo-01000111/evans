"""
Scope: copy the plot and its data to the clipboard, and export it as an
image (PNG at a size and DPI, SVG, PDF, EPS) in either theme.
"""

from __future__ import annotations

import struct

import pytest

pytest.importorskip("PySide6", reason="Qt not available")

from PySide6.QtWidgets import QApplication

from evans.sim.model import SimModel
from evans.sim.solver import simulate
from evans.ui.sim.scope import ScopeWidget
from evans.ui.sim.sim_tab import course_loop


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def scope(app):
    s = ScopeWidget()
    s.resize(500, 300)
    s.show_result(simulate(course_loop(), t_end=5.0, n_points=101))
    yield s
    s.deleteLater()


def _xy_scope():
    m = SimModel("xy")
    m.add("Sine", "s")
    m.add("Clock", "c")
    m.add("XYGraph", "g", title="phase")
    m.connect("c", "g.x")
    m.connect("s", "g.y")
    s = ScopeWidget()
    s.show_result(simulate(m, t_end=1.0, n_points=20))
    s._view.setCurrentText("phase")
    return s


def _png_size(path):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


def test_data_text_is_tab_separated_with_a_header(scope):
    lines = scope.data_text(visible_only=False).split("\n")
    assert lines[0].split("\t") == ["t", "r", "G"] or \
        lines[0].split("\t")[0] == "t"
    assert len(lines) == 102
    assert all(len(row.split("\t")) == len(lines[0].split("\t"))
               for row in lines)


def test_data_text_holds_only_the_visible_range(scope):
    scope._plot.getPlotItem().setXRange(1.0, 2.0, padding=0)
    rows = scope.data_text().split("\n")[1:]
    times = [float(r.split("\t")[0]) for r in rows]
    assert times and min(times) >= 1.0 - 1e-9 and max(times) <= 2.0 + 1e-9
    assert len(times) < 101


def test_copy_puts_image_and_text_on_the_clipboard(scope):
    QApplication.clipboard().clear()
    scope.copy_to_clipboard()
    mime = QApplication.clipboard().mimeData()
    assert mime.hasImage()
    assert mime.text().startswith("t\t")


def test_ctrl_c_and_the_context_menu_copy(scope):
    assert scope._copy_action.shortcut().toString() == "Ctrl+C"
    assert scope._copy_action in scope._plot.getPlotItem().vb.menu.actions()
    QApplication.clipboard().clear()
    scope._copy_action.trigger()
    assert QApplication.clipboard().text().startswith("t\t")


def test_copy_with_no_run_does_nothing(app):
    s = ScopeWidget()
    QApplication.clipboard().setText("keep")
    s.copy_to_clipboard()
    assert QApplication.clipboard().text() == "keep"
    assert s.data_text() == ""
    s.deleteLater()


def test_png_has_the_chosen_size_and_dpi(scope, tmp_path):
    path = tmp_path / "a.png"
    scope.export_image(path, width=4.0, height=2.0, dpi=100)
    assert _png_size(path) == (400, 200)


@pytest.mark.parametrize("ext, magic", [("svg", b"<?xml"), ("pdf", b"%PDF"),
                                        ("eps", b"%!PS")])
def test_vector_formats_are_written(scope, tmp_path, ext, magic):
    path = tmp_path / f"a.{ext}"
    scope.export_image(path)
    assert path.read_bytes().lstrip()[:len(magic)] == magic


def _corner_pixel(path):
    from matplotlib import image
    return image.imread(str(path))[2, 2][:3]


def test_white_page_versus_screen_theme(scope, tmp_path):
    from evans.ui import theme
    white, screen = tmp_path / "w.png", tmp_path / "s.png"
    scope.export_image(white, dpi=50)
    scope.export_image(screen, dpi=50, on_screen=True)
    assert all(_corner_pixel(white) > 0.99)
    expected = theme.tokens().surface.lstrip("#")
    want = [int(expected[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    assert all(abs(a - b) < 0.02 for a, b in zip(_corner_pixel(screen), want))


def test_xy_graph_copies_and_exports(app, tmp_path):
    s = _xy_scope()
    lines = s.data_text().split("\n")
    assert len(lines) == 21 and len(lines[0].split("\t")) == 2
    path = tmp_path / "xy.png"
    s.export_image(path, width=3.0, height=3.0, dpi=60)
    assert _png_size(path) == (180, 180)
    s.deleteLater()


def test_comparison_runs_are_in_the_exported_spec(scope):
    scope.show_result(simulate(course_loop(), t_end=5.0, n_points=101))
    scope._compare.setChecked(True)
    spec = scope.figure_spec()
    assert any("run" in t.label for t in spec.traces)


def test_export_without_a_run_is_refused(app, tmp_path):
    s = ScopeWidget()
    with pytest.raises(ValueError):
        s.export_image(tmp_path / "x.png")
    s.deleteLater()
