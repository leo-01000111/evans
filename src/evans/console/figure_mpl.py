"""
A :class:`~.figures.FigureSpec` drawn with matplotlib.
======================================================
The figure area draws with pyqtgraph, which is fast and themed but has no
3-D axes without OpenGL, and no PostScript output at all. matplotlib — a
hard dependency already, through python-control — has both, so it draws:

* **3-D axes on screen.** :mod:`evans.ui.console.figure_view` puts a
  matplotlib canvas in the figure, with the theme's colours (a
  :class:`Look`), and mplot3d's mouse rotation comes with it.
* **PDF and EPS files** (:func:`save`), on a white page: the formats for a
  paper, from ``saveas``, ``print`` and ``exportgraphics``.
* **The live script's report figures** (:func:`png`).

Every kind and trace style a spec can hold is drawn here, so a figure saves
to PDF however it was made. No Qt is imported: this runs headless.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass, field

import numpy as np

from .figures import FigureSpec, Trace


@dataclass
class Look:
    """The colours a figure is drawn in."""
    background: str = "#ffffff"
    ink: str = "#121314"
    muted: str = "#7a7d82"
    grid: str = "#d0d2d6"
    reference: str = "#1f4fd1"
    danger: str = "#c1122e"
    #: Series colours in turn, when the script set none.
    cycle: tuple[str, ...] = field(default=(
        "#1f4fd1", "#c1122e", "#0d6e37", "#b8860b", "#6a3fb5", "#4b4f55"))
    font: str | None = None


#: The look of a saved file: dark ink on white.
PRINT = Look()

_LEGEND = {"northeast": "upper right", "northwest": "upper left",
           "southeast": "lower right", "southwest": "lower left",
           "north": "upper center", "south": "lower center",
           "east": "center right", "west": "center left", "best": "best",
           "northoutside": "lower center", "southoutside": "upper center",
           "eastoutside": "upper left", "westoutside": "upper right",
           "northeastoutside": "upper left", "northwestoutside": "upper right",
           "southeastoutside": "lower left", "southwestoutside": "lower right"}
_OUTSIDE = {"northoutside": (0.5, 1.02), "southoutside": (0.5, -0.15),
            "eastoutside": (1.02, 1.0), "westoutside": (-0.15, 1.0),
            "northeastoutside": (1.02, 1.0), "northwestoutside": (-0.15, 1.0),
            "southeastoutside": (1.02, 0.0), "southwestoutside": (-0.15, 0.0)}
_MARKERS = {"o": "o", "s": "s", "d": "D", "^": "^", "v": "v", "<": "<",
            ">": ">", "+": "+", "x": "x", "*": "*", ".": ".", "p": "p",
            "h": "h"}
_STYLES = {"-": "-", "--": "--", ":": ":", "-.": "-.", None: "none"}
_COLORBAR = {"east": "right", "west": "left", "north": "top", "south":
             "bottom"}


# ──────────────────────────────────────────────────────────────
#  Entry points
# ──────────────────────────────────────────────────────────────

def save(spec: FigureSpec, path, *, dpi: float | None = None,
         width: float | None = None, height: float | None = None) -> None:
    """Write ``spec`` to ``path`` in the format its extension names."""
    import os

    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    path = os.fspath(path)
    w, h = _size(spec, width, height)
    figure = Figure(figsize=(w, h))
    FigureCanvasAgg(figure)
    draw(figure, spec, PRINT)
    fmt = os.path.splitext(path)[1].lower().lstrip(".")
    figure.savefig(path, format=fmt, dpi=dpi or 150, bbox_inches="tight",
                   facecolor="white")


def png(spec: FigureSpec, *, width: float = 6.4, height: float = 3.6,
        dpi: int = 150) -> bytes:
    """The figure as PNG bytes, for a report."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    if spec.kind == "bode":
        height *= 1.5
    elif spec.kind == "subplot":
        width, height = _size(spec, width, height * 4 / 3)
    figure = Figure(figsize=(width, height))
    FigureCanvasAgg(figure)
    draw(figure, spec, PRINT)
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=dpi)
    return buffer.getvalue()


def _size(spec, width, height) -> tuple[float, float]:
    """A size that gives each subplot room: 4 inches a column, 3 a row."""
    rows, cols = _grid_shape(spec) if spec.kind == "subplot" else (1, 1)
    rows, cols = min(rows, 4), min(cols, 4)
    w = width or (6.4 if cols == 1 else 4.0 * cols)
    h = height or ((7.2 if spec.kind == "bode" else 4.8) if rows == 1
                   else 3.0 * rows)
    return w, h


def draw(figure, spec: FigureSpec, look: Look = PRINT) -> list:
    """Draw ``spec`` on a matplotlib ``Figure``; returns its axes."""
    figure.set_facecolor(look.background)
    if spec.kind == "subplot":
        axes = _subplots(figure, spec, look)
    else:
        axes = _draw_axes(figure, figure.add_gridspec(1, 1)[0, 0], spec,
                          look)
    _annotations(figure, spec, look)
    if spec.kind != "subplot" or not spec.extra.get("tiles"):
        try:
            figure.tight_layout()
        except (ValueError, RuntimeError):
            pass
    return axes


def _grid_shape(spec: FigureSpec) -> tuple[int, int]:
    panes = [p for p in spec.extra.get("panes", []) if p["spec"] is not None]
    rows = math.lcm(*(p["rows"] for p in panes)) if panes else 1
    cols = math.lcm(*(p["cols"] for p in panes)) if panes else 1
    return rows, cols


def _subplots(figure, spec: FigureSpec, look: Look) -> list:
    panes = [p for p in spec.extra.get("panes", []) if p["spec"] is not None]
    rows, cols = _grid_shape(spec)
    grid = figure.add_gridspec(rows, cols)
    axes = []
    for pane in panes:
        m, n = pane["rows"], pane["cols"]
        cells = [c - 1 for c in pane["cells"]]
        r0, r1 = min(c // n for c in cells), max(c // n for c in cells)
        c0, c1 = min(c % n for c in cells), max(c % n for c in cells)
        slot = grid[r0 * rows // m:(r1 + 1) * rows // m,
                    c0 * cols // n:(c1 + 1) * cols // n]
        axes += _draw_axes(figure, slot, pane["spec"], look)
    if spec.title:
        figure.suptitle(spec.title, color=look.ink)
    if spec.extra.get("xlabel"):
        figure.supxlabel(spec.extra["xlabel"], color=look.ink)
    if spec.extra.get("ylabel"):
        figure.supylabel(spec.extra["ylabel"], color=look.ink)
    return axes


# ──────────────────────────────────────────────────────────────
#  One set of axes
# ──────────────────────────────────────────────────────────────

def _draw_axes(figure, slot, spec: FigureSpec, look: Look) -> list:
    if spec.kind == "bode":
        return _bode(figure, slot, spec, look)
    if spec.kind == "pie":
        ax = figure.add_subplot(slot)
        _pie(ax, spec, look)
        _style(ax, look, spec)
        return [ax]
    three = spec.is_3d or _view_3d(spec)
    ax = figure.add_subplot(slot, projection="3d" if three else None)
    _style(ax, look, spec)
    painter = _Painter(ax, spec, look, three)
    painter.paint()
    return [ax]


def _view_3d(spec: FigureSpec) -> bool:
    view = spec.extra.get("view")
    return view is not None and tuple(view) != (0.0, 90.0)


def _style(ax, look: Look, spec: FigureSpec) -> None:
    ax.set_facecolor(look.background)
    ax.tick_params(colors=look.ink, labelsize=8)
    for spine in getattr(ax, "spines", {}).values():
        spine.set_color(look.muted)
    for axis in ("xaxis", "yaxis", "zaxis"):
        part = getattr(ax, axis, None)
        if part is not None:
            part.label.set_color(look.ink)
            if hasattr(part, "set_pane_color"):
                part.set_pane_color((*_rgb(look.background), 1.0))


def _rgb(hex_colour: str) -> tuple[float, float, float]:
    h = hex_colour.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


class _Painter:
    """Draws one axes' traces, then its labels, limits and extras."""

    def __init__(self, ax, spec: FigureSpec, look: Look, three: bool) -> None:
        self.ax = ax
        self.spec = spec
        self.look = look
        self.three = three
        self.right = None                       # yyaxis right's axes
        self.mappable = None                    # what a colorbar shows
        order = spec.extra.get("colororder")
        self.cycle = list(order) if order else list(look.cycle)
        self.n = 0                              # series coloured so far
        cmap = spec.extra.get("colormap")
        self.cmap = _listed(cmap if cmap is not None else _viridis())
        self.clim = colour_limits(spec)

    # ── colours ─────────────────────────────────────────────────

    def colour(self, trace: Trace) -> str:
        colour = trace.props.get("color")
        if self.spec.extra.get("yyaxis") and colour is None:
            return self.cycle[1 % len(self.cycle)] if \
                trace.props.get("side") == "right" else self.cycle[0]
        if colour in (None, "flat", "interp", "auto"):
            colour = self.cycle[self.n % len(self.cycle)]
            self.n += 1
        return self.ink(colour)

    def ink(self, colour):
        """Black on a dark background is drawn in the theme's ink."""
        if colour == "#000000" and _dark(self.look.background):
            return self.look.ink
        return colour

    def norm(self):
        from matplotlib.colors import Normalize
        return Normalize(*self.clim)

    # ── drawing ─────────────────────────────────────────────────

    def paint(self) -> None:
        kind = self.spec.kind
        for trace in self.spec.traces:
            ax = self.ax
            if trace.props.get("side") == "right" and not self.three:
                if self.right is None:
                    self.right = self.ax.twinx()
                    _style(self.right, self.look, self.spec)
                ax = self.right
            if kind == "pzmap":
                marker = "x" if "pole" in trace.label else "o"
                ax.plot(trace.x, trace.y, linestyle="none", marker=marker,
                        markersize=9, markerfacecolor="none",
                        color=self.colour(trace),
                        label=trace.label or None)
                continue
            getattr(self, "_" + trace.style, self._line)(ax, trace)
        self._decorate()

    def _line_style(self, trace: Trace) -> dict:
        p = trace.props
        style = p.get("linestyle", "--" if trace.style == "dashed" else
                      (None if trace.style == "scatter" else "-"))
        marker = p.get("marker", "o" if trace.style == "scatter" else None)
        kw = {"linestyle": _STYLES.get(style, "-"),
              "linewidth": p.get("linewidth", 1.4),
              "label": trace.label or None}
        if marker:
            kw["marker"] = _MARKERS.get(marker, "o")
            kw["markersize"] = p.get("markersize", 6 if marker != "." else 8)
            if p.get("markerface") not in (None, "auto"):
                kw["markerfacecolor"] = p["markerface"] \
                    if p["markerface"] != "none" else "none"
            elif marker in "osd^v<>ph":
                kw["markerfacecolor"] = "none"
            if p.get("markeredge") not in (None, "auto"):
                kw["markeredgecolor"] = p["markeredge"]
        return kw

    def _line(self, ax, trace: Trace) -> None:
        kw = self._line_style(trace)
        if self.three:
            ax.plot(trace.x, trace.y, np.zeros_like(trace.x),
                    color=self.colour(trace), **kw)
        else:
            ax.plot(trace.x, trace.y, color=self.colour(trace), **kw)

    _dashed = _line

    def _scatter(self, ax, trace: Trace) -> None:
        if not trace.props and self.spec.kind != "xy":
            return self._line(ax, trace)
        self._markers(ax, trace, None)

    def _scatter3(self, ax, trace: Trace) -> None:
        self._markers(ax, trace, trace.z)

    def _markers(self, ax, trace: Trace, z) -> None:
        p = trace.props
        colour = None if p.get("cdata") is not None or p.get("colors") \
            else self.colour(trace)
        colours = p.get("colors") or colour
        kw = {"s": p.get("sizes", p.get("markersize", 6) ** 2 if
                         "markersize" in p else 36),
              "marker": _MARKERS.get(p.get("marker") or "o", "o"),
              "label": trace.label or None,
              "linewidths": p.get("linewidth", 1.0)}
        if p.get("cdata") is not None:
            kw.update(c=p["cdata"], cmap=self.cmap, norm=self.norm())
        filled = p.get("filled") or kw["marker"] in ("+", "x", "*", ".")
        if p.get("cdata") is not None:
            if not filled:
                kw["facecolors"] = "none"
        elif filled:
            kw["color"] = colours
        else:
            kw.update(facecolors="none", edgecolors=colours)
        if z is None and self.three:
            z = np.zeros_like(trace.x)
        args = (trace.x, trace.y) if z is None else (trace.x, trace.y, z)
        artist = ax.scatter(*args, **kw)
        if p.get("cdata") is not None:
            self.mappable = artist

    def _stem(self, ax, trace: Trace) -> None:
        colour = self.colour(trace)
        ax.vlines(trace.x, 0, trace.y, color=colour, linewidth=1.2)
        ax.plot(trace.x, trace.y, "o", markerfacecolor="none", color=colour,
                label=trace.label or None)

    def _bar(self, ax, trace: Trace) -> None:
        width = self.spec.extra.get("bar_width", 0.8)
        base = trace.props.get("base")
        colour = self.colour(trace)
        values = trace.y - (base if base is not None else 0)
        if trace.props.get("horizontal"):
            ax.barh(trace.x, values, height=width, left=base, color=colour,
                    edgecolor=self.look.ink, linewidth=0.5,
                    label=trace.label or None)
        else:
            ax.bar(trace.x, values, width=width, bottom=base, color=colour,
                   edgecolor=self.look.ink, linewidth=0.5,
                   label=trace.label or None)

    def _errorbar(self, ax, trace: Trace) -> None:
        p = trace.props
        kw = self._line_style(trace)

        def pair(neg, pos):
            if neg is None and pos is None:
                return None
            n = np.zeros_like(trace.x) if neg is None else neg
            q = np.zeros_like(trace.x) if pos is None else pos
            return np.vstack([n, q])

        ax.errorbar(trace.x, trace.y, yerr=pair(p.get("yneg"), p.get("ypos")),
                    xerr=pair(p.get("xneg"), p.get("xpos")),
                    color=self.colour(trace), capsize=3, **kw)

    def _area(self, ax, trace: Trace) -> None:
        colour = self.colour(trace)
        ax.fill_between(trace.x, trace.props.get("base", 0), trace.y,
                        facecolor=colour, alpha=trace.props.get("alpha", 1.0),
                        edgecolor=self.look.ink, linewidth=0.6,
                        label=trace.label or None)

    def _face(self, trace: Trace):
        """A polygon's fill: its colour, or its colour-mapped value."""
        p = trace.props
        if p.get("cdata") is not None:
            value = float(np.nanmean(np.asarray(p["cdata"], float)))
            return self.cmap(self.norm()(value))
        colour = p.get("color")
        if colour == "none":
            return "none"
        return self.ink(colour) if colour not in (None, "flat", "interp") \
            else self.colour(trace)

    def _fill(self, ax, trace: Trace) -> None:
        p = trace.props
        edge = p.get("edgecolor", "#000000")
        ax.fill(trace.x, trace.y, facecolor=self._face(trace),
                edgecolor=self.ink(edge) if edge != "none" else "none",
                alpha=p.get("alpha", 1.0), linewidth=p.get("linewidth", 0.8),
                label=trace.label or None)

    def _fill3(self, ax, trace: Trace) -> None:
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
        p = trace.props
        edge = p.get("edgecolor", "#000000")
        poly = Poly3DCollection([np.column_stack([trace.x, trace.y,
                                                  trace.z])],
                                facecolor=self._face(trace),
                                edgecolor=self.ink(edge) if edge != "none"
                                else "none", alpha=p.get("alpha", 1.0))
        ax.add_collection3d(poly)
        ax.auto_scale_xyz(trace.x, trace.y, trace.z, had_data=True)

    def _image(self, ax, trace: Trace) -> None:
        C = np.asarray(trace.z, float)
        rows, cols = C.shape[:2]
        (x0, x1), (y0, y1) = trace.x[:2], trace.y[:2]
        dx = (x1 - x0) / (cols - 1) if cols > 1 else 1.0
        dy = (y1 - y0) / (rows - 1) if rows > 1 else 1.0
        extent = (x0 - dx / 2, x1 + dx / 2, y0 - dy / 2, y1 + dy / 2)
        if C.ndim == 3:                      # true colour: RGB in [0, 1]
            self.mappable = None
            ax.imshow(np.clip(np.nan_to_num(C), 0, 1), extent=extent,
                      origin="lower", aspect="auto", interpolation="nearest")
            return
        if trace.props.get("direct"):
            from matplotlib.colors import Normalize
            norm = Normalize(1, self.cmap.N + 1)
        else:
            norm = self.norm()
        self.mappable = ax.imshow(C, extent=extent, origin="lower",
                                  cmap=self.cmap, norm=norm, aspect="auto",
                                  interpolation="nearest")

    def _levels(self, trace: Trace, filled: bool) -> np.ndarray:
        levels = np.asarray(trace.props.get("levels", []), float)
        if not filled:
            return levels
        lo, hi = trace.props.get("zrange", (np.nanmin(trace.z),
                                            np.nanmax(trace.z)))
        bounds = np.unique(np.concatenate([[lo], levels, [hi]]))
        return bounds if bounds.size > 1 else np.array([lo, lo + 1])

    def _contour(self, ax, trace: Trace) -> None:
        self._contours(ax, trace, filled=False)

    def _contourf(self, ax, trace: Trace) -> None:
        self._contours(ax, trace, filled=True)

    def _contours(self, ax, trace: Trace, filled: bool) -> None:
        p = trace.props
        levels = self._levels(trace, filled)
        if not levels.size:
            return
        kw = {"levels": levels}
        if p.get("color") not in (None, "flat"):
            kw["colors"] = self.ink(p["color"])
        else:
            kw.update(cmap=self.cmap, norm=self.norm())
        if filled:
            artist = ax.contourf(trace.x, trace.y, trace.z, **kw)
            ax.contour(trace.x, trace.y, trace.z, levels=levels,
                       colors=self.look.ink, linewidths=0.5)
        else:
            artist = ax.contour(trace.x, trace.y, trace.z,
                                linewidths=p.get("linewidth", 1.0),
                                linestyles=_STYLES.get(p.get("linestyle",
                                                             "-"), "-"), **kw)
        if p.get("showtext"):
            ax.clabel(artist, fontsize=7, colors=self.look.ink)
        if "colors" not in kw:
            self.mappable = artist

    def _contour3(self, ax, trace: Trace) -> None:
        levels = self._levels(trace, False)
        if levels.size:
            ax.contour(trace.x, trace.y, trace.z, levels=levels, zdir="z",
                       offset=trace.props.get("base", 0.0), cmap=self.cmap,
                       norm=self.norm())

    def _quiver(self, ax, trace: Trace) -> None:
        p = trace.props
        if self.three:
            zero = np.zeros_like(trace.x)
            ax.quiver(trace.x, trace.y, zero, p["u"], p["v"], zero,
                      color=self.colour(trace), arrow_length_ratio=0.3)
            return
        ax.quiver(trace.x, trace.y, p["u"], p["v"], angles="xy",
                  scale_units="xy", scale=1, color=self.colour(trace),
                  width=0.004, label=trace.label or None)

    def _quiver3(self, ax, trace: Trace) -> None:
        p = trace.props
        ax.quiver(trace.x, trace.y, trace.z, p["u"], p["v"], p["w"],
                  color=self.colour(trace), arrow_length_ratio=0.3,
                  label=trace.label or None)
        # Arrows do not widen 3-D limits by themselves; their tips must.
        ax.auto_scale_xyz(np.concatenate([trace.x, trace.x + p["u"]]),
                          np.concatenate([trace.y, trace.y + p["v"]]),
                          np.concatenate([trace.z, trace.z + p["w"]]),
                          had_data=True)

    def _line3(self, ax, trace: Trace) -> None:
        ax.plot(trace.x, trace.y, trace.z, color=self.colour(trace),
                **self._line_style(trace))

    def _surface(self, ax, trace: Trace) -> None:
        p = trace.props
        shading = p.get("shading", "faceted")
        values = p.get("cdata", trace.z)
        face = p.get("color")
        edge = p.get("edgecolor")
        kw = {"rstride": 1, "cstride": 1, "alpha": p.get("alpha", 1.0),
              "antialiased": shading != "faceted"}
        if face not in (None, "flat", "interp", "auto"):
            kw["color"] = face if face != "none" else self.look.background
        else:
            kw["facecolors"] = self.cmap(self.norm()(_faces(values)))
        if edge == "none" or (edge is None and shading != "faceted"):
            kw.update(linewidth=0, edgecolor="none")
        else:
            kw.update(linewidth=0.3, edgecolor=self.ink(edge or "#000000"))
        surface = ax.plot_surface(trace.x, trace.y, trace.z, **kw)
        if "facecolors" in kw:
            self.mappable = _scalar_mappable(self.cmap, self.norm())
        return surface

    def _mesh(self, ax, trace: Trace) -> None:
        values = trace.props.get("cdata", trace.z)
        edges = self.cmap(self.norm()(_faces(values))).reshape(-1, 4)
        face = trace.props.get("color")
        surface = ax.plot_surface(
            trace.x, trace.y, trace.z, rstride=1, cstride=1,
            color=self.look.background if face in (None, "flat", "interp")
            else face, linewidth=0.6, shade=False)
        surface.set_edgecolor(edges)
        self.mappable = _scalar_mappable(self.cmap, self.norm())

    # ── everything but the data ─────────────────────────────────

    def _decorate(self) -> None:
        ax, spec, look, extra = self.ax, self.spec, self.look, self.spec.extra
        if spec.kind == "nyquist":
            theta = np.linspace(0, 2 * np.pi, 200)
            ax.plot(np.cos(theta), np.sin(theta), "--", color=look.muted,
                    linewidth=0.8)
            ax.plot([-1], [0], "x", color=look.danger, markersize=10)
            ax.set_aspect("equal", adjustable="datalim")
        # An explicit ``grid on`` on a Nyquist or Nichols chart means its own
        # grid, M-circles or the M/N-contours, in place of the rectangular one.
        chart_grid = str(extra.get("grid", "")).lower() == "on" and \
            not self.three and (spec.kind == "nyquist" or extra.get("nichols"))
        if chart_grid:
            (self._m_circles if spec.kind == "nyquist" else self._ngrid)()
        if spec.kind in ("nyquist", "pzmap", "rlocus"):
            ax.axhline(0, color=look.muted, linewidth=0.6)
            ax.axvline(0, color=look.muted, linewidth=0.6)
        if extra.get("logx"):
            ax.set_xscale("log")
        if extra.get("logy"):
            ax.set_yscale("log")
        for entry in extra.get("xlines", []) if not self.three else []:
            self._refline(ax.axvline, entry, vertical=True)
        for entry in extra.get("ylines", []) if not self.three else []:
            self._refline(ax.axhline, entry, vertical=False)
        for entry in extra.get("texts", []):
            self._text(entry)
        title = spec.title
        if extra.get("subtitle"):
            title = f"{title}\n{extra['subtitle']}" if title else \
                extra["subtitle"]
        ax.set_title(title, color=look.ink, fontsize=10)
        ax.set_xlabel(spec.xlabel)
        ax.set_ylabel(spec.ylabel)
        right = extra.get("right", {})
        if self.right is not None or extra.get("yyaxis"):
            if self.right is None and not self.three:
                self.right = ax.twinx()
                _style(self.right, look, spec)
            if self.right is not None:
                self.right.set_ylabel(right.get("ylabel", ""), color=look.ink)
                if right.get("ylim") is not None:
                    self.right.set_ylim(*map(float, right["ylim"]))
                if not any(t.props.get("color") for t in spec.traces):
                    ax.tick_params(axis="y", colors=self.cycle[0])
                    self.right.tick_params(axis="y",
                                           colors=self.cycle[1 % len(
                                               self.cycle)])
        if self.three:
            ax.set_zlabel(extra.get("zlabel", ""))
            az, el = extra.get("view") or (-37.5, 30.0)
            ax.view_init(elev=el, azim=az - 90)
        if extra.get("tight"):
            ax.autoscale(enable=True, tight=True)
        for axis in ("x", "y") + (("z",) if self.three else ()):
            lims = extra.get(axis + "lim")
            if lims is not None:
                getattr(ax, f"set_{axis}lim")(*map(float, lims))
        if extra.get("aspect") == "equal":
            ax.set_aspect("equal", adjustable="box" if self.three
                          else "datalim")
        if extra.get("ydir") == "reverse":
            ax.invert_yaxis()
        if extra.get("grid", "on") != "off" and not extra.get("axis_off") \
                and not chart_grid \
                and any(t.style not in ("image",) for t in spec.traces):
            ax.grid(True, color=look.grid, linewidth=0.6, alpha=0.8)
        if extra.get("axis_off"):
            ax.set_axis_off()
        if extra.get("colorbar") and self.mappable is not None:
            location = extra["colorbar"].get("location", "eastoutside")
            side = next((v for k, v in _COLORBAR.items()
                         if location.startswith(k)), "right")
            bar = ax.figure.colorbar(self.mappable, ax=ax, location=side)
            bar.ax.tick_params(colors=look.ink, labelsize=8)
            if extra["colorbar"].get("label"):
                bar.set_label(extra["colorbar"]["label"], color=look.ink)
        self._legend()

    # ── control charts' own grids ───────────────────────────────

    #: The closed-loop gains (dB) and phases (°) MATLAB's grids are drawn at.
    NYQUIST_DB = (-20, -10, -6, -4, -2, 0, 2, 4, 6, 10, 20)
    NICHOLS_DB = (6, 3, 1, 0.5, 0.25, 0, -1, -3, -6, -12, -20, -40)
    NICHOLS_DEG = (-1, -5, -10, -20, -30, -45, -60, -90, -120, -150)

    def _m_circles(self) -> None:
        """``|T|`` constant on the Nyquist plane, labelled in dB, under the data."""
        from ..core.freqresp import m_circle

        ax, look = self.ax, self.look
        ax.apply_aspect()           # the view "equal" widens the data's to
        xlim, ylim = ax.get_xlim(), ax.get_ylim()
        for db in self.NYQUIST_DB:
            M = 10 ** (db / 20)
            path = m_circle(M) if db else -0.5 + 1j * np.array([-1e3, 1e3])
            ax.plot(path.real, path.imag, ":", color=look.muted,
                    linewidth=0.6, zorder=0)
            # Each circle's top, or for 0 dB the line at the top of the view.
            if db:
                centre, radius = -M ** 2 / (M ** 2 - 1), abs(M / (M ** 2 - 1))
                x, y = centre, radius
            else:
                x, y = -0.5, ylim[1]
            if xlim[0] <= x <= xlim[1] and ylim[0] <= y <= ylim[1]:
                ax.text(x, y, f"{db:g} dB", fontsize=7, color=look.muted,
                        ha="center", va="bottom" if db else "top",
                        clip_on=True)
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)

    def _ngrid(self) -> None:
        """
        The Nichols chart: closed-loop gain (M) and phase (N) contours,
        repeated every 360° across the phase the data spans.
        """
        from ..core.freqresp import nichols_m_contour, nichols_n_contour

        ax, look = self.ax, self.look
        xlim, ylim = ax.get_xlim(), ax.get_ylim()
        shifts = range(int(np.floor(xlim[0] / 360.0)),
                       int(np.ceil(xlim[1] / 360.0)) + 1)
        families = [(f"{db:g} dB", nichols_m_contour(10 ** (db / 20)), True)
                    for db in self.NICHOLS_DB]
        families += [(f"{deg:g}°", nichols_n_contour(deg), False)
                     for deg in self.NICHOLS_DEG]
        width, height = xlim[1] - xlim[0], ylim[1] - ylim[0]
        placed: list[tuple[float, float]] = []
        for label, pts, is_gain in families:
            if not len(pts):
                continue
            for k in shifts:
                phase, mag = pts[:, 0] + 360.0 * k, pts[:, 1]
                ax.plot(phase, mag, ":", color=look.muted, linewidth=0.6,
                        zorder=0)
                seen = (np.isfinite(mag) & (phase >= xlim[0])
                        & (phase <= xlim[1]) & (mag >= ylim[0])
                        & (mag <= ylim[1]))
                if not seen.any():
                    continue
                # Gain contours are labelled at the top of their crossing of
                # the critical −180°; phase contours all meet there, so at
                # their lowest visible point instead, where they fan out.
                score = np.abs(phase - (360.0 * k - 180.0)) - 1e-9 * mag \
                    if is_gain else mag
                i = int(np.argmin(np.where(seen, score, np.inf)))
                # Near −180°, 0 dB every contour crowds in: label only those
                # with room, as an unreadable pile helps nobody.
                spot = ((phase[i] - xlim[0]) / width, (mag[i] - ylim[0]) / height)
                if any(abs(spot[0] - u) < 0.06 and abs(spot[1] - v) < 0.035
                       for u, v in placed):
                    continue
                placed.append(spot)
                ax.text(phase[i], mag[i], label, fontsize=7,
                        color=look.muted, ha="center", va="bottom",
                        clip_on=True)
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)

    def _refline(self, draw, entry: dict, vertical: bool) -> None:
        colour = self.ink(entry.get("color", "#262626"))
        if _dark(self.look.background) and colour == "#262626":
            colour = self.look.ink
        draw(entry["value"], color=colour,
             linestyle=_STYLES.get(entry.get("linestyle", "-"), "-"),
             linewidth=entry.get("linewidth", 0.8))
        if entry.get("label"):
            if vertical:
                self.ax.text(entry["value"], 1.0, " " + entry["label"],
                             transform=self.ax.get_xaxis_transform(),
                             rotation=90, va="top", ha="right", fontsize=8,
                             color=colour)
            else:
                self.ax.text(1.0, entry["value"], entry["label"] + " ",
                             transform=self.ax.get_yaxis_transform(),
                             va="bottom", ha="right", fontsize=8,
                             color=colour)

    def _text(self, entry: dict) -> None:
        kw = {"ha": entry.get("halign", "left"),
              "va": {"middle": "center", "cap": "top"}.get(
                  entry.get("valign", "middle"), entry.get("valign", "center")),
              "color": self.ink(entry.get("color", self.look.ink)),
              "fontsize": entry.get("fontsize", 9),
              "rotation": entry.get("rotation", 0)}
        if entry.get("fontweight") == "bold":
            kw["fontweight"] = "bold"
        if entry.get("background") not in (None, "none"):
            kw["bbox"] = {"facecolor": entry["background"],
                          "edgecolor": "none"}
        if self.three:
            self.ax.text(entry["x"], entry["y"], entry.get("z", 0.0),
                         entry["string"], **kw)
        else:
            self.ax.text(entry["x"], entry["y"], entry["string"], **kw)

    def _legend(self) -> None:
        extra = self.spec.extra
        if extra.get("legend") == "off" or self.spec.kind == "rlocus":
            return
        handles, labels = self.ax.get_legend_handles_labels()
        if self.right is not None:
            h2, l2 = self.right.get_legend_handles_labels()
            handles, labels = handles + h2, labels + l2
        if not labels:
            return
        location = extra.get("legend_location", "northeast")
        kw = {"loc": _LEGEND.get(location, "upper right"), "fontsize": 8}
        if location in _OUTSIDE:
            kw["bbox_to_anchor"] = _OUTSIDE[location]
        legend = self.ax.legend(handles, labels, **kw)
        legend.get_frame().set_facecolor(self.look.background)
        for text in legend.get_texts():
            text.set_color(self.look.ink)


def colour_limits(spec: FigureSpec) -> tuple[float, float]:
    """
    The data range the colour map spans: ``caxis``'s, else that of every
    image, surface, contour and colour-mapped marker on the axes.
    """
    lims = spec.extra.get("clim")
    if lims is not None:
        return tuple(float(v) for v in lims)
    values = []
    for t in spec.traces:
        if t.style in ("image", "surface", "mesh", "contour", "contourf",
                       "contour3") and not t.props.get("direct"):
            values.append(t.props.get("cdata", t.z))
        elif t.props.get("cdata") is not None:
            values.append(t.props["cdata"])
    values = [np.asarray(v, float).reshape(-1) for v in values
              if v is not None]
    data = np.concatenate(values) if values else np.array([])
    data = data[np.isfinite(data)]
    if not data.size:
        return (0.0, 1.0)
    lo, hi = float(data.min()), float(data.max())
    return (lo, hi) if hi > lo else (lo - 0.5, hi + 0.5)


def _faces(values) -> np.ndarray:
    """A grid's values averaged over each face, as a surface is coloured."""
    V = np.asarray(values, float)
    if V.shape[0] < 2 or V.shape[1] < 2:
        return V
    return (V[:-1, :-1] + V[1:, :-1] + V[:-1, 1:] + V[1:, 1:]) / 4


def _scalar_mappable(cmap, norm):
    from matplotlib.cm import ScalarMappable
    mappable = ScalarMappable(norm=norm, cmap=cmap)
    mappable.set_array([])
    return mappable


def _listed(cmap: np.ndarray):
    from matplotlib.colors import ListedColormap
    return ListedColormap(np.asarray(cmap, float))


def _viridis() -> np.ndarray:
    import matplotlib
    return np.asarray(matplotlib.colormaps["viridis"](np.linspace(0, 1, 256)))[
        :, :3]


def _dark(colour: str) -> bool:
    r, g, b = _rgb(colour)
    return 0.299 * r + 0.587 * g + 0.114 * b < 0.5


# ──────────────────────────────────────────────────────────────
#  Kinds with axes of their own
# ──────────────────────────────────────────────────────────────

def _bode(figure, slot, spec: FigureSpec, look: Look) -> list:
    inner = slot.subgridspec(2, 1, hspace=0.08)
    mag = figure.add_subplot(inner[0])
    phase = figure.add_subplot(inner[1], sharex=mag)
    for ax in (mag, phase):
        _style(ax, look, spec)
    cycle = list(spec.extra.get("colororder") or look.cycle)
    for i, t in enumerate(spec.traces):
        mag.semilogx(t.x, t.y, color=cycle[i % len(cycle)],
                     label=t.label or None)
    for i, (omega, degrees, _label) in enumerate(spec.extra.get("phase", [])):
        phase.semilogx(omega, degrees, color=cycle[i % len(cycle)])
    mag.set_ylabel("|G| (dB)")
    phase.set_ylabel("Phase (°)")
    phase.set_xlabel(spec.xlabel or "ω (rad/s)")
    mag.set_title(spec.title or "Bode", color=look.ink, fontsize=10)
    for ax in (mag, phase):
        ax.grid(True, color=look.grid, linewidth=0.6, alpha=0.8)
    if any(t.label for t in spec.traces):
        mag.legend(fontsize=8)
    return [mag, phase]


def _pie(ax, spec: FigureSpec, look: Look) -> None:
    trace = spec.traces[0]
    fractions = np.asarray(trace.y, float)
    cmap = spec.extra.get("colormap")
    cmap = np.asarray(cmap if cmap is not None else _viridis())
    picks = np.linspace(0, len(cmap) - 1, max(len(fractions), 1)).astype(int)
    wedges, texts = ax.pie(
        fractions, labels=trace.props.get("labels"),
        explode=0.1 * np.asarray(trace.props.get("explode"), float),
        colors=[cmap[k] for k in picks], startangle=90, counterclock=False,
        normalize=False, wedgeprops={"edgecolor": look.ink, "linewidth": 0.6},
        textprops={"color": look.ink, "fontsize": 9})
    ax.set_aspect("equal")
    if spec.title:
        ax.set_title(spec.title, color=look.ink, fontsize=10)
    labelled = [t.label for t in spec.traces if t.label]
    if labelled and spec.extra.get("legend") != "off":
        ax.legend(wedges, labelled, fontsize=8)


def _annotations(figure, spec: FigureSpec, look: Look) -> None:
    """``annotation`` shapes, in fractions of the figure."""
    from matplotlib.lines import Line2D
    from matplotlib.patches import Ellipse, FancyArrowPatch, Rectangle

    for a in spec.extra.get("annotations", []):
        colour = a.get("color") or look.ink
        if colour == "#000000" and _dark(look.background):
            colour = look.ink
        width = a.get("linewidth", 1.0)
        kind = a["type"]
        if kind in ("line", "arrow", "doublearrow", "textarrow"):
            (x0, x1), (y0, y1) = a["x"][:2], a["y"][:2]
            if kind == "line":
                figure.add_artist(Line2D([x0, x1], [y0, y1], color=colour,
                                         linewidth=width,
                                         transform=figure.transFigure))
            else:
                style = "<->" if kind == "doublearrow" else "->"
                figure.add_artist(FancyArrowPatch(
                    (x0, y0), (x1, y1), arrowstyle=style, mutation_scale=12,
                    color=colour, linewidth=width,
                    transform=figure.transFigure))
            if kind == "textarrow" and a.get("string"):
                figure.text(x0, y0, a["string"], color=colour, fontsize=9,
                            ha="right" if x1 > x0 else "left", va="center")
            continue
        x, y, w, h = a["position"][:4]
        face = a.get("color") if kind != "textbox" else a.get("background")
        face = face if face not in (None, "none") else "none"
        edge = a.get("edgecolor", colour)
        edge = look.ink if edge == "#000000" and _dark(look.background) \
            else edge
        if kind == "ellipse":
            figure.add_artist(Ellipse((x + w / 2, y + h / 2), w, h,
                                      facecolor=face, edgecolor=edge,
                                      linewidth=width,
                                      transform=figure.transFigure))
        else:
            figure.add_artist(Rectangle((x, y), w, h, facecolor=face,
                                        edgecolor=edge if edge != "none"
                                        else "none", linewidth=width,
                                        transform=figure.transFigure))
        if a.get("string"):
            figure.text(x + 0.01, y + h - 0.01, a["string"], color=colour,
                        fontsize=a.get("fontsize", 9), ha="left", va="top")
