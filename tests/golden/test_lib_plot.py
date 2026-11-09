"""
Phase 3's plotting: what each plot function puts in a figure spec, the
MATLAB rules it follows, and the matplotlib renderer that saves PDF and EPS.

These run headless, against the recording sink: no widget is drawn. What
the figure area does with a spec is in ``test_plot_ui.py``.
"""

from __future__ import annotations

import numpy as np
import pytest

from evans.console import Interpreter, figure_mpl, set_figure_sink
from evans.console.figures import recording_sink
from evans.console.matlab_runtime import _is_linespec


@pytest.fixture
def sink():
    recorder = recording_sink()
    previous = set_figure_sink(recorder)
    yield recorder
    set_figure_sink(previous)


@pytest.fixture
def it(sink):
    return Interpreter()


def run(it, source: str):
    results = it.run_script(source, "matlab")
    failed = [r for r in results if r.error]
    assert not failed, f"{failed[0].source!r} → {failed[0].error}"


def fails(it, source: str) -> str:
    results = it.run_script(source, "matlab")
    errors = [r.error for r in results if r.error]
    assert errors, f"{source!r} should have failed"
    return errors[0]


def last(sink):
    return sink.figures[-1]


# ── line specs, colours, options ─────────────────────────────────

@pytest.mark.parametrize("spec", ["r--o", "o-r", "--", ":", "x", "k", "-.b",
                                  "sm"])
def test_line_specs_in_any_order(spec):
    assert _is_linespec(spec)


@pytest.mark.parametrize("text", ["off", "filled", "LineWidth", "rr", "o-x",
                                  ""])
def test_words_are_not_line_specs(text):
    assert not _is_linespec(text)


def test_plot_honours_colour_marker_and_width(it, sink):
    run(it, "plot(1:3, [1 4 9], 'r--o', 'LineWidth', 2, 'DisplayName', 'sq')")
    t = last(sink).traces[0]
    assert t.props["color"] == "#ff0000"
    assert t.props["linestyle"] == "--" and t.props["marker"] == "o"
    assert t.props["linewidth"] == 2.0 and t.label == "sq"


def test_colour_options_take_names_hex_and_triplets(it, sink):
    run(it, "plot(1:3, 'Color', [0 0.5 1]); hold on\n"
            "plot(1:3, 'Color', 'magenta'); plot(1:3, 'Color', '#abc')")
    assert [t.props["color"] for t in last(sink).traces] == \
        ["#0080ff", "#ff00ff", "#aabbcc"]


def test_a_bad_colour_says_so(it):
    assert "between 0 and 1" in fails(it, "plot(1:3, 'Color', [2 0 0])")


# ── 2-D plot types ───────────────────────────────────────────────

def test_scatter_sizes_colours_and_fill(it, sink):
    run(it, "scatter(1:4, 1:4, [10 20 30 40], [1 2 3 4], 'filled', 'd')")
    t = last(sink).traces[0]
    assert t.style == "scatter" and t.props["marker"] == "d"
    assert t.props["filled"] and list(t.props["sizes"]) == [10, 20, 30, 40]
    assert list(t.props["cdata"]) == [1, 2, 3, 4]


def test_scatter_with_one_colour_and_default_size(it, sink):
    run(it, "scatter(1:3, 1:3, [], 'red')")
    t = last(sink).traces[0]
    assert t.props["color"] == "#ff0000" and "sizes" not in t.props


def test_errorbar_symmetric_uneven_and_horizontal(it, sink):
    run(it, "errorbar(1:3, [2 4 6], [1 1 1])")
    t = last(sink).traces[0]
    assert list(t.props["yneg"]) == [1, 1, 1] and "xneg" not in t.props
    run(it, "errorbar(1:3, [2 4 6], [1 1 1], [2 2 2])")
    t = last(sink).traces[0]
    assert list(t.props["ypos"]) == [2, 2, 2]
    run(it, "errorbar(1:3, [2 4 6], [1 2 3], 'horizontal')")
    t = last(sink).traces[0]
    assert list(t.props["xpos"]) == [1, 2, 3] and "ypos" not in t.props


def test_errorbar_with_a_marker_spec_draws_no_line(it, sink):
    run(it, "errorbar([1 2 3], [0.1 0.1 0.1], 'o')")
    assert last(sink).traces[0].props["linestyle"] is None


def test_area_stacks_columns(it, sink):
    run(it, "area([1 2 3], [1 1; 2 2; 3 1])")
    low, high = last(sink).traces
    assert list(low.props["base"]) == [0, 0, 0] and list(low.y) == [1, 2, 3]
    assert list(high.props["base"]) == [1, 2, 3]
    assert list(high.y) == [2, 4, 4]


def test_bar_stacked_and_horizontal(it, sink):
    run(it, "bar([1 2; 3 4], 'stacked')")
    first, second = last(sink).traces
    assert list(second.props["base"]) == [1, 3] and list(second.y) == [3, 7]
    run(it, "barh([3 1 2])")
    assert last(sink).traces[0].props["horizontal"]


def test_fill_draws_one_polygon_a_column(it, sink):
    run(it, "fill([0 2; 1 3; 0 2], [0 0; 0 0; 1 1], 'g')")
    traces = last(sink).traces
    assert [t.style for t in traces] == ["fill", "fill"]
    assert traces[0].props["color"] == "#00ff00"


def test_patch_adds_to_the_axes_without_hold(it, sink):
    run(it, "plot(1:3)\npatch([1 2 2], [1 1 2], 'b', 'FaceAlpha', 0.3)")
    spec = last(sink)
    assert [t.style for t in spec.traces] == ["line", "fill"]
    assert spec.traces[1].props["alpha"] == 0.3


def test_patch_by_faces_and_vertices(it, sink):
    run(it, "patch('Faces', [1 2 3; 2 3 4], 'Vertices', [0 0; 1 0; 0 1; 1 1],"
            " 'FaceColor', 'r')")
    traces = last(sink).traces
    assert len(traces) == 2 and list(traces[1].x) == [1, 0, 1]


def test_pie_fractions_labels_and_partial_pies(it, sink):
    run(it, "pie([1 1 2])")
    t = last(sink).traces[0]
    assert last(sink).kind == "pie"
    assert np.allclose(t.y, [0.25, 0.25, 0.5])
    assert t.props["labels"] == ["25%", "25%", "50%"]
    run(it, "pie([0.2 0.3], {'a', 'b'})")        # sums below 1: left partial
    t = last(sink).traces[0]
    assert np.allclose(t.y, [0.2, 0.3]) and t.props["labels"] == ["a", "b"]


def test_text_and_reference_lines(it, sink):
    run(it, "plot(1:3); text(2, 2, 'mid', 'Color', 'r', 'FontSize', 12)\n"
            "xline([1 2], '--', 'edge'); yline(1.5)")
    extra = last(sink).extra
    assert extra["texts"] == [{"x": 2.0, "y": 2.0, "string": "mid",
                               "color": "#ff0000", "fontsize": 12.0}]
    assert [e["value"] for e in extra["xlines"]] == [1.0, 2.0]
    assert extra["xlines"][0]["linestyle"] == "--"
    assert extra["xlines"][1]["label"] == "edge"
    assert extra["ylines"][0]["value"] == 1.5


def test_text_on_several_points(it, sink):
    run(it, "plot(1:3); text([1 2], [1 2], {'a', 'b'})")
    assert [t["string"] for t in last(sink).extra["texts"]] == ["a", "b"]


def test_yyaxis_puts_plots_and_labels_on_each_side(it, sink):
    run(it, "yyaxis left; plot(1:3); ylabel('L')\n"
            "yyaxis right; plot([3 2 1]); ylabel('R'); ylim([0 5])\n"
            "plot([9 9 9])")               # replaces only the right side
    spec = last(sink)
    assert [t.props["side"] for t in spec.traces] == ["left", "right"]
    assert list(spec.traces[1].y) == [9, 9, 9]
    assert spec.ylabel == "L" and spec.extra["right"] == {
        "ylabel": "R", "ylim": (0.0, 5.0)}


def test_yyaxis_needs_a_side(it):
    assert "left" in fails(it, "yyaxis up")


# ── layouts ──────────────────────────────────────────────────────

def test_tiledlayout_places_spans_where_they_fit(it, sink):
    run(it, "t = tiledlayout(2, 2);\nnexttile; plot(1:3)\n"
            "nexttile([1 2]); plot(3:-1:1)\ntitle(t, 'All'); xlabel(t, 'time')")
    grid = last(sink)
    assert grid.kind == "subplot" and grid.title == "All"
    assert grid.extra["xlabel"] == "time"
    assert [p["cells"] for p in grid.extra["panes"]] == [(1,), (3, 4)]


def test_a_full_layout_says_so(it):
    assert "full" in fails(it, "tiledlayout(1, 1); nexttile; nexttile")


def test_a_flow_layout_regrids_as_it_grows(it, sink):
    run(it, "tiledlayout('flow')\nfor k = 1:5\n  nexttile; plot(1:k)\nend")
    panes = last(sink).extra["panes"]
    assert {(p["rows"], p["cols"]) for p in panes} == {(2, 3)}
    assert [p["cells"] for p in panes] == [(1,), (2,), (3,), (4,), (5,)]


def test_nexttile_without_a_layout_starts_one(it, sink):
    run(it, "nexttile; plot(1:3); nexttile; plot(1:4)")
    assert len(last(sink).extra["panes"]) == 2


def test_an_axes_handle_picks_the_tile(it, sink):
    run(it, "tiledlayout(1, 2)\nax1 = nexttile; ax2 = nexttile;\n"
            "plot(ax1, 1:3); title(ax1, 'left')\nplot(ax2, 1:5)")
    left, right = (p["spec"] for p in last(sink).extra["panes"])
    assert left.title == "left" and len(left.traces[0].x) == 3
    assert len(right.traces[0].x) == 5


def test_subplot_returns_a_handle_too(it, sink):
    run(it, "a = subplot(2, 1, 1); subplot(2, 1, 2); plot(1:3)\n"
            "plot(a, 1:4); title(a, 'top')")
    top, bottom = (p["spec"] for p in last(sink).extra["panes"])
    assert top.title == "top" and len(top.traces[0].x) == 4


def test_annotations_belong_to_the_figure(it, sink):
    run(it, "plot(1:3)\nannotation('arrow', [0.1 0.4], [0.2 0.5])\n"
            "annotation('textbox', [0.1 0.1 0.2 0.1], 'String', 'note')")
    shapes = last(sink).extra["annotations"]
    assert shapes[0] == {"type": "arrow", "x": [0.1, 0.4], "y": [0.2, 0.5]}
    assert shapes[1]["string"] == "note" and shapes[1]["position"] == \
        [0.1, 0.1, 0.2, 0.1]


def test_an_annotation_box_needs_four_numbers(it):
    assert "four" in fails(it, "plot(1:3); annotation('rectangle', [0 0 1])")


def test_colororder_colours_the_figure_and_reads_back(it, sink):
    run(it, "colororder([1 0 0; 0 0 1]); plot(1:3); hold on; plot(3:-1:1)")
    assert last(sink).extra["colororder"] == ["#ff0000", "#0000ff"]
    run(it, "figure; c = colororder;")
    assert np.allclose(it.namespace["c"][0], [0, 0.447, 0.741])


# ── 3-D ──────────────────────────────────────────────────────────

def test_plot3_is_3d(it, sink):
    run(it, "plot3([1 2 3], [1 2 3], [0 1 0], 'o')")
    spec = last(sink)
    assert spec.is_3d and spec.traces[0].style == "scatter3"
    assert list(spec.traces[0].z) == [0, 1, 0]


def test_surf_turns_vectors_into_a_grid(it, sink):
    run(it, "surf(1:3, 1:2, [1 2 3; 4 5 6]); zlabel('h'); zlim([0 10])")
    spec = last(sink)
    t = spec.traces[0]
    assert t.style == "surface" and t.x.shape == (2, 3)
    assert spec.extra["zlabel"] == "h" and spec.extra["zlim"] == (0.0, 10.0)


def test_surf_checks_the_grid(it):
    assert "columns" in fails(it, "surf(1:4, 1:2, [1 2 3; 4 5 6])")


def test_mesh_shading_and_view(it, sink):
    run(it, "mesh(peaks(5)); shading interp; view(30, 45)\n[az, el] = view;")
    spec = last(sink)
    assert spec.traces[0].style == "mesh"
    assert spec.traces[0].props["shading"] == "interp"
    assert spec.extra["view"] == (30.0, 45.0)
    assert (it.namespace["az"], it.namespace["el"]) == (30.0, 45.0)


def test_view_2_and_3(it, sink):
    run(it, "surf(peaks(4)); view(2)")
    assert last(sink).extra["view"] == (0.0, 90.0)
    run(it, "plot(1:3); view(3)")
    assert last(sink).extra["view"] == (-37.5, 30.0)
    assert figure_mpl._view_3d(last(sink))


def test_peaks_is_matlabs_function():
    it = Interpreter()
    run(it, "[X, Y, Z] = peaks(3);")
    x, y = -3.0, -3.0
    z = (3 * (1 - x) ** 2 * np.exp(-x ** 2 - (y + 1) ** 2)
         - 10 * (x / 5 - x ** 3 - y ** 5) * np.exp(-x ** 2 - y ** 2)
         - np.exp(-(x + 1) ** 2 - y ** 2) / 3)
    assert it.namespace["Z"].shape == (3, 3)
    assert it.namespace["Z"][0, 0] == pytest.approx(z)
    assert list(it.namespace["X"][0]) == [-3, 0, 3]


def test_contour_levels(it, sink):
    run(it, "contour(peaks(20), 4)")
    t = last(sink).traces[0]
    lo, hi = t.props["zrange"]
    assert np.allclose(t.props["levels"], np.linspace(lo, hi, 6)[1:-1])
    run(it, "contour(peaks(20), [1 1])")
    assert list(last(sink).traces[0].props["levels"]) == [1.0]
    run(it, "contourf(peaks(20))")
    levels = last(sink).traces[0].props["levels"]
    assert 4 <= len(levels) <= 12 and np.allclose(np.diff(levels),
                                                  levels[1] - levels[0])


def test_the_contour_matrix(it):
    run(it, "[X, Y] = meshgrid(-2:0.1:2);\nC = contour(X, Y, X.^2 + Y.^2, [1 1]);")
    C = it.namespace["C"]
    assert C[0, 0] == 1.0
    n = int(C[1, 0])
    points = C[:, 1:n + 1]
    assert np.allclose(np.hypot(points[0], points[1]), 1.0, atol=0.01)


def test_quiver_scales_like_matlab(it, sink):
    run(it, "quiver([0 1], [0 0], [2 4], [0 0])")
    t = last(sink).traces[0]
    # Two points a column apart (spacing 1/2 each way): the longest arrow,
    # 4, is scaled to 0.9 of the spacing's length.
    spacing = np.hypot(1 / np.sqrt(2), 0)
    assert max(np.hypot(t.props["u"], t.props["v"])) == pytest.approx(
        0.9 * spacing)
    run(it, "quiver([0 1], [0 0], [2 4], [0 0], 0)")
    assert list(last(sink).traces[0].props["u"]) == [2, 4]


def test_quiver3(it, sink):
    run(it, "quiver3(0, 0, 0, 1, 2, 3, 0)")
    t = last(sink).traces[0]
    assert last(sink).is_3d and (t.props["u"][0], t.props["w"][0]) == (1, 3)


# ── images and colour ────────────────────────────────────────────

def test_imagesc_places_and_scales(it, sink):
    run(it, "imagesc([10 20], [1 5], rand(5, 3), [0 2])")
    spec = last(sink)
    t = spec.traces[0]
    assert t.style == "image" and list(t.x) == [10, 20] and list(t.y) == [1, 5]
    assert spec.extra["clim"] == (0.0, 2.0) and spec.extra["ydir"] == "reverse"


def test_image_maps_values_directly(it, sink):
    run(it, "image([1 2; 3 4])")
    assert last(sink).traces[0].props["direct"]


def test_imshow_is_gray_from_0_to_1_unless_told(it, sink):
    run(it, "imshow([0 0.5; 1 2])")
    spec = last(sink)
    assert spec.extra["clim"] == (0.0, 1.0) and spec.extra["axis_off"]
    assert np.allclose(spec.extra["colormap"][-1], [1, 1, 1])
    run(it, "imshow([0 50; 100 200], [])")
    assert last(sink).extra["clim"] == (0.0, 200.0)


def test_colormaps_by_name_and_function(it, sink):
    run(it, "m = jet(4); g = gray(3);")
    assert it.namespace["m"].shape == (4, 3)
    assert np.allclose(it.namespace["g"], [[0, 0, 0], [0.5, 0.5, 0.5],
                                           [1, 1, 1]], atol=0.01)
    run(it, "surf(peaks(5)); colormap(hot); c = colormap;")
    assert it.namespace["c"].shape == (256, 3)
    assert last(sink).extra["colormap"] is not None


def test_colormap_errors(it):
    assert "not a colour map" in fails(it, "colormap('nosuchmap')")
    assert "n-by-3" in fails(it, "colormap([1 2])")


def test_colorbar_and_caxis(it, sink):
    run(it, "imagesc([1 2; 3 4]); colorbar; caxis([1 5]); l = caxis;")
    spec = last(sink)
    assert spec.extra["colorbar"]["location"] == "eastoutside"
    assert list(it.namespace["l"]) == [1, 5]
    run(it, "imagesc([1 2; 3 4]); colorbar; clim([1 5])\n"
            "colorbar('off'); clim auto; m = clim;")
    assert "colorbar" not in last(sink).extra
    assert list(it.namespace["m"]) == [1, 4]


def test_axis_modes_and_reading_limits(it, sink):
    run(it, "plot([1 4], [2 8]); axis equal; axis tight; axis ij; v = axis;")
    extra = last(sink).extra
    assert extra["aspect"] == "equal" and extra["tight"]
    assert extra["ydir"] == "reverse"
    assert list(it.namespace["v"]) == [1, 4, 2, 8]
    run(it, "plot([1 4], [2 8]); axis equal; axis ij\n"
            "axis xy; axis normal; axis([0 1 0 1 0 1])")
    extra = last(sink).extra
    assert "ydir" not in extra and "aspect" not in extra
    assert extra["zlim"] == (0.0, 1.0)


def test_axis_rejects_unknown_words(it):
    assert "unknown" in fails(it, "plot(1:3); axis sideways")


# ── figures at the prompt ────────────────────────────────────────

def test_a_title_typed_later_reaches_the_figure(sink):
    it = Interpreter()
    it.command("plot(1:3)")
    spec = last(sink)
    assert it.command("title('later'); xlabel('x')").ok
    assert last(sink) is spec and spec.title == "later"
    assert spec.xlabel == "x"


def test_hold_lasts_from_one_prompt_to_the_next(sink):
    it = Interpreter()
    it.command("plot(1:3)")
    it.command("hold on")
    it.command("plot(3:-1:1)")
    assert len(last(sink).traces) == 2
    it.command("hold off")
    it.command("plot(1:2)")
    assert len(last(sink).traces) == 1


def test_a_closed_figure_is_not_brought_back(sink):
    it = Interpreter()
    it.command("plot(1:3)")
    spec = last(sink)
    it.figure_open = lambda s: s is not spec
    count = len(sink.figures)
    it.command("hold on; title('x')")
    assert len(sink.figures) == count, "an empty title draws nothing"
    it.command("plot(1:2)")
    assert last(sink) is not spec and len(last(sink).traces) == 1


def test_an_untouched_figure_is_not_sent_again(sink):
    it = Interpreter()
    it.command("plot(1:3)")
    count = len(sink.figures)
    it.command("x = 2;")
    assert len(sink.figures) == count


def test_a_script_starts_without_the_last_runs_figures(sink):
    it = Interpreter()
    it.run_script("plot(1:3); hold on", "matlab")
    it.run_script("plot(1:2)", "matlab")
    assert len(last(sink).traces) == 1


# ── saving ───────────────────────────────────────────────────────

@pytest.mark.parametrize("ext, magic", [("pdf", b"%PDF"), ("eps", b"%!PS")])
def test_exportgraphics_writes_vector_files_headless(it, tmp_path, ext, magic):
    run(it, f"cd('{tmp_path.as_posix()}')\nsurf(peaks(10)); title('s')\n"
            f"exportgraphics(gcf, 'f.{ext}')\nprint('-d{ext}', 'g')")
    assert (tmp_path / f"f.{ext}").read_bytes().startswith(magic)
    assert (tmp_path / f"g.{ext}").read_bytes().startswith(magic)


def test_exportgraphics_needs_an_extension(it):
    assert "extension" in fails(it, "plot(1:3); exportgraphics(gcf, 'f')")


#: One figure of every kind and style the renderer knows.
EVERY_STYLE = [
    "plot(1:3, 'r--o')", "scatter(1:5, 1:5, 40, 1:5, 'filled')",
    "errorbar(1:3, 1:3, [1 1 1], 'both')", "area([1 2; 2 1])",
    "bar([1 2; 3 4], 'stacked')", "barh([1 2])", "fill([0 1 0], [0 0 1], 'r')",
    "pie([1 2 3], [0 1 0])", "plot(1:3); text(2, 2, 'a'); xline(2); yline(2)",
    "yyaxis left; plot(1:3); yyaxis right; plot(3:-1:1); ylabel('r')",
    "t = tiledlayout(1, 2); nexttile; plot(1:3); nexttile; surf(peaks(5));"
    " title(t, 'mixed')",
    "plot(1:3); annotation('doublearrow', [0.2 0.8], [0.5 0.5]);"
    " annotation('ellipse', [0.3 0.3 0.2 0.2])",
    "plot3(1:3, 1:3, 1:3)", "scatter3(1:3, 1:3, 1:3, [], 1:3)",
    "surfc(peaks(10)); colorbar", "mesh(peaks(10))",
    "contour(peaks(20), 'ShowText', 'on')", "contourf(peaks(20)); colorbar",
    "quiver(rand(3), rand(3))", "quiver3(0, 0, 0, 1, 1, 1)",
    "fill3([0 1 0], [0 0 1], [0 1 1], 'b')",
    "imagesc(peaks(10)); colorbar", "image([1 2; 3 4])", "imshow(rand(5))",
    "stem(1:3)", "semilogy(1:3, [1 10 100])",
]


@pytest.mark.parametrize("command", EVERY_STYLE)
def test_every_style_saves_as_pdf(it, sink, tmp_path, command):
    run(it, command)
    path = tmp_path / "f.pdf"
    figure_mpl.save(last(sink), path)
    assert path.read_bytes().startswith(b"%PDF")


def test_a_new_plot_does_not_redraw_the_one_before(sink):
    it = Interpreter()
    it.command("plot(1:3)")
    first = last(sink)
    it.command("plot(1:4)")
    assert sum(spec is first for spec in sink.figures) == 1


# ── the control charts' own grids ────────────────────────────────

def _drawn(spec):
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    figure = Figure()
    FigureCanvasAgg(figure)
    (ax,) = figure_mpl.draw(figure, spec)
    return ax


def test_grid_on_draws_m_circles_on_a_nyquist_diagram(it, sink):
    run(it, "L = tf(4, [1 3 3 1]); nyquist(L)")
    plain = _drawn(last(sink))
    run(it, "L = tf(4, [1 3 3 1]); nyquist(L); grid on")
    ax = _drawn(last(sink))
    labels = {t.get_text() for t in ax.texts}
    assert "0 dB" in labels and "6 dB" in labels
    assert len(ax.lines) > len(plain.lines) + 5
    assert not ax.xaxis.get_gridlines()[0].get_visible()
    # The circles do not stretch the view the data set.
    assert ax.get_xlim() == pytest.approx(plain.get_xlim())


def test_nyquistoptions_grid_draws_the_m_circles(it, sink):
    run(it, "o = nyquistoptions; o.Grid = 'on'; "
            "nyquist(tf(4, [1 3 3 1]), o)")
    assert last(sink).extra["grid"] == "on"


def test_ngrid_draws_gain_and_phase_contours(it, sink):
    run(it, "nichols(tf(20, [1 6 5 0])); ngrid")
    spec = last(sink)
    assert spec.extra["nichols"] and spec.extra["grid"] == "on"
    labels = {t.get_text() for t in _drawn(spec).texts}
    assert any(t.endswith(" dB") for t in labels)
    assert any(t.endswith("°") for t in labels)


def test_grid_on_a_nichols_chart_is_ngrid(it, sink):
    run(it, "nichols(tf(20, [1 6 5 0])); grid on")
    assert any(t.get_text().endswith("dB") for t in _drawn(last(sink)).texts)


def test_ngrid_new_holds_for_the_plot_that_follows(it, sink):
    run(it, "ngrid('new'); nichols(tf(20, [1 6 5 0]))")
    spec = last(sink)
    assert spec.extra.get("grid") == "on" and spec.traces


def test_a_plain_nyquist_has_no_m_circles(it, sink):
    run(it, "nyquist(tf(4, [1 3 3 1]))")
    assert not _drawn(last(sink)).texts


# ── figure(n), gcf, close(n), clf ────────────────────────────────

def test_figure_numbers_count_up_from_one(it, sink):
    run(it, "plot(1:3)\nn1 = gcf;\nplot(1:4)\nn2 = gcf;")
    assert (int(it.namespace["n1"]), int(it.namespace["n2"])) == (1, 2)
    assert [s.number for s in sink.figures] == [1, 2]


def test_figure_returns_the_number_its_plot_will_get(it):
    run(it, "a = figure; plot(1:3); b = figure; plot(1:3);")
    assert (int(it.namespace["a"]), int(it.namespace["b"])) == (1, 2)


def test_figure_n_goes_back_and_the_next_plot_replaces_it(it, sink):
    run(it, "plot(1:3)\nplot(1:4)\nfigure(1)\nn = gcf;\nplot([5 6 7])")
    assert it.namespace["n"] == 1
    assert len(set(map(id, sink.figures))) == 2     # nothing new was opened
    first = sink.figures[0]
    assert first.number == 1 and first.traces[0].y.tolist() == [5, 6, 7]


def test_figure_n_opens_a_figure_that_is_not_there(it, sink):
    run(it, "figure(5)\nn = gcf;\nplot(1:3)")
    assert it.namespace["n"] == 5
    assert last(sink).number == 5
    run(it, "figure\nplot(1:2)")
    assert last(sink).number == 1          # the lowest free number


def test_figure_n_must_be_a_positive_integer(it):
    assert "positive integer" in fails(it, "figure(0)")
    assert "positive integer" in fails(it, "figure(1.5)")


def test_figure_n_ignores_name_value_pairs(it):
    run(it, "figure(2, 'Name', 'Bode')\nn = gcf;")
    assert it.namespace["n"] == 2


def test_figure_n_can_hold_on_the_figure_it_went_back_to(it, sink):
    run(it, "plot(1:3)\nhold on\nplot(3:-1:1)\nfigure(2)\nplot(1:2)\n"
            "figure(1)\nhold on\nplot([2 2 2])")
    first = sink.figures[0]
    assert first.number == 1 and len(first.traces) == 3


def test_figure_n_returns_to_a_subplot_grid(it, sink):
    run(it, "subplot(2,1,1); plot(1:3); subplot(2,1,2); plot(3:-1:1)\n"
            "figure(2); plot(1:2)\nfigure(1)\nn = gcf;")
    assert it.namespace["n"] == 1
    assert sink.figures[0].kind == "subplot"


def test_gcf_follows_the_prompt_between_lines(it):
    it.command("plot(1:3)")
    it.command("plot(1:4)")
    it.command("figure(1)")
    assert it.command("n = gcf;").ok and it.namespace["n"] == 1


def test_close_n_leaves_the_others_and_frees_the_number(it):
    it.command("plot(1:3)")
    it.command("plot(1:4)")
    it.command("plot(1:5)")
    it.command("close(2)")
    runtime = it._matlab_runtime()
    assert sorted(s.number for s in runtime.figures.specs) == [1, 3]
    it.command("figure(1)")
    assert it.command("n = gcf;").ok and it.namespace["n"] == 1
    it.command("figure")            # the freed number comes round again
    assert it.command("n = gcf;").ok and it.namespace["n"] == 2


def test_close_with_no_argument_closes_the_current_figure(it):
    it.command("plot(1:3)")
    it.command("plot(1:4)")
    it.command("close")
    runtime = it._matlab_runtime()
    assert [s.number for s in runtime.figures.specs] == [1]


def test_close_all_and_a_missing_figure(it):
    it.command("plot(1:3)")
    it.command("close all")
    assert "Invalid figure handle" in fails(it, "close(7)")


def test_clf_empties_the_figure_but_keeps_its_number(it, sink):
    run(it, "plot(1:3)\nn1 = gcf;\nclf\nn2 = gcf;\nplot([4 5 6])")
    assert it.namespace["n1"] == it.namespace["n2"] == 1
    assert len(set(map(id, sink.figures))) == 1
    assert sink.figures[0].traces[0].y.tolist() == [4, 5, 6]


def test_clf_on_a_subplot_grid_leaves_a_plain_figure(it):
    it.command("subplot(2,1,1); plot(1:3)")
    it.command("clf")
    spec = it._matlab_runtime().figures.specs[0]
    assert spec.kind == "xy" and not spec.traces and spec.number == 1
