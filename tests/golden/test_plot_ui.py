"""
Phase 3's plots in the figure area: each style draws, 3-D axes and pies get
a matplotlib canvas, data tips pin, images read out, ``yyaxis right`` has an
axis of its own, and a figure saves as PDF, EPS and higher-resolution PNG.

Where the figure comes from is ``test_lib_plot.py``'s business; these take
its specs and draw them.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402

from evans.console import Interpreter, set_figure_sink  # noqa: E402
from evans.console.figures import recording_sink  # noqa: E402

from .test_lib_plot import EVERY_STYLE  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def spec_of():
    """Run MATLAB and return the figure spec it drew last."""
    sink = recording_sink()
    previous = set_figure_sink(sink)

    def run(source: str):
        results = Interpreter().run_script(source, "matlab")
        failed = [r.error for r in results if r.error]
        assert not failed, failed[0]
        return sink.figures[-1]

    yield run
    set_figure_sink(previous)


def _view(app, spec):
    from evans.ui.console.figure_view import FigureView

    view = FigureView(spec)
    view.resize(640, 480)
    view.show()
    for _ in range(5):
        app.processEvents()
    return view


@pytest.mark.parametrize("command", EVERY_STYLE)
def test_every_style_draws(app, spec_of, command):
    view = _view(app, spec_of(command))
    three = "plot3" in command or "surf" in command or "mesh" in command \
        or "scatter3" in command or "quiver3" in command \
        or "fill3" in command or "pie" in command
    assert view.drawn_with_matplotlib() == three
    view.close()


def test_a_3d_figure_is_a_matplotlib_canvas_with_a_readout(app, spec_of):
    view = _view(app, spec_of("surf(peaks(10)); view(20, 40)"))
    assert len(view.canvases) == 1 and not view.plot_widgets()
    axes = view.canvases[0].figure.axes[0]
    assert axes.name == "3d"
    assert (axes.azim, axes.elev) == (20 - 90, 40)
    view.close()


def test_a_data_tip_pins_where_you_click(app, spec_of):
    view = _view(app, spec_of("plot(1:10, (1:10).^2)"))
    tips = view.tips[0]
    hit = tips.hit_at(3.0, 9.0)
    assert hit is not None and "x = 3" in hit.text and "y = 9" in hit.text
    tips.pin(hit)
    assert len(tips.pinned) == 1
    tips.clear()
    assert tips.pinned == []
    view.close()


def test_an_image_reads_out_its_pixels(app, spec_of):
    view = _view(app, spec_of("imagesc([1 2 3; 4 5 6])"))
    hit = view.tips[0].hit_at(2.0, 2.0)
    assert hit is not None and "Value = 5" in hit.text
    assert view.tips[0].hit_at(10.0, 10.0) is None
    view.close()


def test_yyaxis_right_has_its_own_view(app, spec_of):
    from evans.ui.console import figure_view

    view = _view(app, spec_of("yyaxis left; plot(1:3)\n"
                              "yyaxis right; plot([30 20 10]); ylim([0 40])"))
    plot = view.plot_widgets()[0].getPlotItem()
    assert plot.getAxis("right").isVisible()
    boxes = [i for i in plot.scene().items()
             if type(i).__name__ == "ViewBox" and i is not plot.vb]
    assert len(boxes) == 1
    assert boxes[0].viewRange()[1] == pytest.approx([0, 40])
    assert figure_view.COLORS[1].lower() in \
        plot.getAxis("right").pen().color().name()
    view.close()


def test_annotations_are_painted_over_the_figure(app, spec_of):
    view = _view(app, spec_of("plot(1:3); annotation('arrow', [0.2 0.5],"
                              " [0.2 0.5])"))
    assert view._overlay is not None
    assert view._overlay.geometry() == view.rect()
    view.close()


def test_a_tiled_layouts_shared_labels(app, spec_of):
    from PySide6.QtWidgets import QLabel

    view = _view(app, spec_of("t = tiledlayout(1, 2); nexttile; plot(1:3)\n"
                              "nexttile; plot(1:4); title(t, 'Both')\n"
                              "xlabel(t, 'shared x'); ylabel(t, 'shared y')"))
    texts = {label.text() for label in view.findChildren(QLabel)}
    assert {"Both", "shared x"} <= texts
    assert len(view.plot_widgets()) == 2
    view.close()


@pytest.mark.parametrize("ext, magic", [
    ("pdf", b"%PDF"), ("eps", b"%!PS"), ("jpg", b"\xff\xd8"),
    ("tif", b"II"), ("svg", b"<?xml")])
def test_a_figure_saves_in_every_format(app, spec_of, tmp_path, ext, magic):
    from evans.ui.console.figure_view import export_figure

    view = _view(app, spec_of("contourf(peaks(20)); colorbar"))
    path = export_figure(view, tmp_path / f"f.{ext}")
    assert path.read_bytes().startswith(magic) and view.saved
    view.close()


def test_a_3d_figure_saves_as_svg_through_matplotlib(app, spec_of, tmp_path):
    from evans.ui.console.figure_view import export_figure

    view = _view(app, spec_of("surf(peaks(8))"))
    text = export_figure(view, tmp_path / "s.svg").read_text("utf-8")
    assert "<svg" in text and "matplotlib" in text.lower()
    view.close()


def test_resolution_scales_a_picture(app, spec_of, tmp_path):
    from PySide6.QtGui import QImage

    from evans.ui.console.figure_view import export_figure

    view = _view(app, spec_of("plot(1:3)"))
    export_figure(view, tmp_path / "a.png")
    export_figure(view, tmp_path / "b.png", dpi=192)
    a, b = QImage(str(tmp_path / "a.png")), QImage(str(tmp_path / "b.png"))
    assert b.width() == pytest.approx(2 * a.width(), abs=2)
    view.close()


def test_a_rebuild_keeps_the_view_and_its_number(app, spec_of):
    spec = spec_of("plot(1:3)")
    view = _view(app, spec)
    view.number = 4
    spec.title = "amended"
    view.rebuild()
    assert view.number == 4
    plot = view.plot_widgets()[0].getPlotItem()
    assert "amended" in plot.titleLabel.text
    view.close()
