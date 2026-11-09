"""
Plotting.
=========
Figures and axes (``figure``, ``subplot``, ``tiledlayout``/``nexttile``,
``hold``, ``yyaxis``), the 2-D plots (``plot`` and its log-axis cousins,
``scatter``, ``errorbar``, ``bar``, ``area``, ``fill``/``patch``, ``pie``,
``stem``, ``stairs``, histograms, ``quiver``, ``contour``), the 3-D ones
(``plot3``, ``scatter3``, ``surf``, ``mesh``, ``quiver3``, ``view``), images
and colour (``imagesc``, ``image``, ``imshow``, ``colormap``, ``colorbar``,
``caxis``, ``colororder``), annotation (``title`` … ``legend``, ``text``,
``xline``/``yline``, ``annotation``) and saving (``saveas``, ``print``,
``exportgraphics``).

A mixin of :class:`.matlab_runtime._Library`, imported the way
:mod:`.lib_stats` explains. Each function describes what to draw in a
:class:`~.figures.FigureSpec` and hands it to the run's
:class:`~.matlab_runtime.Figures`; it draws nothing itself. The figure area
draws a spec with pyqtgraph (:mod:`evans.ui.console.figure_view`), or with
matplotlib when it needs 3-D axes; :mod:`.figure_mpl` also writes PDF and
EPS files and the live script's report figures.

Data are reduced here to what a renderer needs, so the two renderers agree:
contour levels are chosen, arrows scaled and areas stacked before a spec
leaves this module.
"""

from __future__ import annotations

import math
import os
import re

import numpy as np

from . import matlab_runtime as _mr  # noqa: F401
from .figures import FigureSpec
from .matlab_runtime import (
    Cell,
    Figures,
    Graphic,
    MatlabError,
    Struct,
    _as2d,
    _as_text,
    _is_linespec,
    _is_number,
    _nargout,
    _normalise,
    _numel,
    _scalar_of,
)

# ──────────────────────────────────────────────────────────────
#  Colours, line specifications and name–value pairs
# ──────────────────────────────────────────────────────────────

_LETTERS = {"r": (1, 0, 0), "g": (0, 1, 0), "b": (0, 0, 1), "c": (0, 1, 1),
            "m": (1, 0, 1), "y": (1, 1, 0), "k": (0, 0, 0), "w": (1, 1, 1)}
_NAMES = {"red": "r", "green": "g", "blue": "b", "cyan": "c",
          "magenta": "m", "yellow": "y", "black": "k", "white": "w"}

#: MATLAB's default line colours (the "gem" palette), which ``lines`` and
#: ``colororder('gem')`` return.
GEM = np.array([[0.0000, 0.4470, 0.7410], [0.8500, 0.3250, 0.0980],
                [0.9290, 0.6940, 0.1250], [0.4940, 0.1840, 0.5560],
                [0.4660, 0.6740, 0.1880], [0.3010, 0.7450, 0.9330],
                [0.6350, 0.0780, 0.1840]])


def _hex(rgb) -> str:
    return "#" + "".join(f"{round(255 * min(max(float(v), 0.0), 1.0)):02x}"
                         for v in rgb)


def _colour(value, who: str = "") -> str | None:
    """A MATLAB colour — letter, name, hex or RGB triplet — as ``#rrggbb``."""
    if value is None:
        return None
    if isinstance(value, str):
        low = value.strip().lower()
        if low == "none":
            return "none"
        low = _NAMES.get(low, low)
        if low in _LETTERS:
            return _hex(_LETTERS[low])
        if re.fullmatch(r"#[0-9a-f]{6}", low):
            return low
        if re.fullmatch(r"#[0-9a-f]{3}", low):
            return "#" + "".join(c * 2 for c in low[1:])
        raise MatlabError(f"{who}: '{value}' is not a colour name, a "
                          f"colour letter or a hex code.".lstrip(": "))
    a = np.asarray(value, float).reshape(-1)
    if a.size != 3:
        raise MatlabError(f"{who}: a colour is an RGB triplet [r g b]."
                          .lstrip(": "))
    if a.min() < 0 or a.max() > 1:
        raise MatlabError(f"{who}: RGB values must be between 0 and 1."
                          .lstrip(": "))
    return _hex(a)


def _linespec(text: str) -> dict:
    """``'r--o'`` → its line style, marker and colour, those it names."""
    out: dict = {}
    rest = text
    for style in ("--", "-.", "-", ":"):
        if style in rest:
            out["linestyle"] = style
            rest = rest.replace(style, "", 1)
            break
    for ch in rest:
        if ch in _LETTERS:
            out["color"] = _hex(_LETTERS[ch])
        elif ch in ".o+*xsd^v<>ph":
            out["marker"] = ch
    return out


def _style(linespec: str) -> str:
    """The trace style a line spec asks for: line, dashed, or bare markers."""
    if not linespec:
        return "line"
    if any(s in linespec for s in ("--", ":", "-.")):
        return "dashed"
    if "-" not in linespec and re.search(r"[.o+*xsd^v<>ph]", linespec):
        return "scatter"
    return "line"


_MARKER_NAMES = {"none": None, "square": "s", "diamond": "d",
                 "pentagram": "p", "hexagram": "h", "circle": "o"}

#: The name–value pairs a renderer uses, and how each is read: MATLAB's
#: name → (the ``Trace.props`` key, the kind of value). Any other name is
#: accepted and ignored, as before.
_PROPS = {
    "color": ("color", "colour"),
    "linewidth": ("linewidth", "number"),
    "markersize": ("markersize", "number"),
    "markerfacecolor": ("markerface", "face"),
    "markeredgecolor": ("markeredge", "face"),
    "facecolor": ("color", "face"),
    "edgecolor": ("edgecolor", "face"),
    "facealpha": ("alpha", "number"),
    "linestyle": ("linestyle", "text"),
    "marker": ("marker", "marker"),
    "displayname": ("label", "text"),
    "levellist": ("levels", "array"),
    "showtext": ("showtext", "onoff"),
    "fontsize": ("fontsize", "number"),
    "fontweight": ("fontweight", "text"),
    "horizontalalignment": ("halign", "text"),
    "verticalalignment": ("valign", "text"),
    "rotation": ("rotation", "number"),
    "string": ("string", "label"),
    "basevalue": ("base", "number"),
    "autoscale": ("autoscale", "onoff"),
    "autoscalefactor": ("scale", "number"),
    "backgroundcolor": ("background", "face"),
    "xdata": ("xdata", "array"),
    "ydata": ("ydata", "array"),
    "zdata": ("zdata", "array"),
    "cdata": ("cdata", "array"),
    "faces": ("faces", "array"),
    "vertices": ("vertices", "array"),
    "facevertexcdata": ("cdata", "array"),
    "position": ("position", "array"),
    "label": ("label", "label"),
    "location": ("location", "text"),
}


def _set_prop(props: dict, name: str, value) -> None:
    entry = _PROPS.get(name)
    if entry is None:
        return
    key, kind = entry
    if kind == "colour":
        props[key] = _colour(value, name)
    elif kind == "face":
        word = value.lower() if isinstance(value, str) else None
        props[key] = word if word in ("flat", "interp", "none", "auto") \
            else _colour(value, name)
    elif kind == "number":
        props[key] = float(_scalar_of(value))
    elif kind == "onoff":
        props[key] = (value.lower() == "on") if isinstance(value, str) \
            else bool(_scalar_of(value))
    elif kind == "marker":
        word = str(value).lower()
        props[key] = _MARKER_NAMES.get(word, word[:1] or None)
    elif kind == "array":
        props[key] = np.asarray(value, float)
    elif kind == "label":
        props[key] = _label_text(value)
    else:
        props[key] = value.lower() if key in ("linestyle", "halign",
                                              "valign", "location") \
            else str(value)
    if key == "linestyle" and props[key] == "none":
        props[key] = None


def _label_text(value) -> str:
    """Text for a label: a char array, or a cell's lines joined."""
    if isinstance(value, Cell):
        return "\n".join(_as_text(v) for v in value)
    return _as_text(value)


def _options(args, flags=(), start: int = 0) -> tuple[list, dict, set]:
    """
    Split a plot call's arguments: data (including line specs), then the
    name–value pairs, then the bare flags it knows (``'filled'``…). The
    first ``start`` arguments are data whatever they are — a ``text``
    call's string.
    """
    data, props, seen = list(args[:start]), {}, set()
    k = start
    while k < len(args):
        a = args[k]
        if isinstance(a, str):
            low = a.lower()
            if low in flags:
                seen.add(low)
                k += 1
            elif _is_linespec(a) or low in _NAMES:
                data.append(a)
                k += 1
            else:
                if k + 1 < len(args):
                    _set_prop(props, low, args[k + 1])
                k += 2
            continue
        data.append(a)
        k += 1
    return data, props, seen


def _apply_linespec(props: dict, spec: str) -> dict:
    """The line spec's style, marker and colour, under explicit options."""
    return {**_linespec(spec), **props}


def _vector(x) -> np.ndarray:
    return np.real(np.asarray(x, float).reshape(-1)) if not np.iscomplexobj(
        x) else np.real(np.asarray(x).reshape(-1)).astype(float)


def _grid(X, Y, Z, who: str):
    """``X``, ``Y`` as matrices the shape of ``Z``, from vectors or matrices."""
    Z = _as2d(np.asarray(Z, float))
    m, n = Z.shape
    if X is None:
        X, Y = np.arange(1.0, n + 1), np.arange(1.0, m + 1)
    X, Y = np.asarray(X, float), np.asarray(Y, float)
    if X.ndim <= 1 or 1 in X.shape:
        X = X.reshape(-1)
        Y = Y.reshape(-1)
        if X.size != n or Y.size != m:
            raise MatlabError(f"{who}: length(X) must equal the number of "
                              f"columns of Z and length(Y) its rows.")
        X, Y = np.meshgrid(X, Y)
    if X.shape != Z.shape or Y.shape != Z.shape:
        raise MatlabError(f"{who}: X, Y and Z must be the same size.")
    return X, Y, Z


def _nice_levels(lo: float, hi: float, n: int | None = None) -> np.ndarray:
    """Contour levels inside (lo, hi): ``n`` evenly spaced, else round ones."""
    if not (np.isfinite(lo) and np.isfinite(hi)) or lo == hi:
        return np.array([lo])
    if n is not None:
        return np.linspace(lo, hi, n + 2)[1:-1]
    step = 10 ** math.floor(math.log10((hi - lo) / 8))
    for factor in (1, 2, 2.5, 5, 10):
        if (hi - lo) / (step * factor) <= 10:
            step *= factor
            break
    levels = np.arange(math.ceil(lo / step) * step, hi, step)
    levels = levels[(levels > lo) & (levels < hi)]
    return levels if levels.size else np.array([(lo + hi) / 2])


def _colormap(name: str, n: int = 256) -> np.ndarray:
    """A colour map by MATLAB's name, as an n×3 array of RGB in [0, 1]."""
    low = name.lower()
    if low == "lines":
        return GEM[np.arange(n) % len(GEM)]
    if low == "white":
        return np.ones((n, 3))
    import matplotlib
    # parula is MathWorks' own; viridis is the open map closest to it.
    mapped = {"parula": "viridis", "default": "viridis"}.get(low, low)
    try:
        cmap = matplotlib.colormaps[mapped]
    except KeyError:
        raise MatlabError(f"'{name}' is not a colour map.") from None
    return np.asarray(cmap(np.linspace(0, 1, n)))[:, :3]


#: Colour-map functions, each ``name(n)`` returning an n×3 map.
COLORMAPS = ("parula", "jet", "turbo", "hot", "cool", "gray", "bone",
             "copper", "pink", "hsv", "spring", "summer", "autumn", "winter",
             "lines", "white")


def _contour_matrix(X, Y, Z, levels) -> np.ndarray:
    """MATLAB's contour matrix: per line a [level; count] column, then points."""
    import contourpy
    gen = contourpy.contour_generator(X, Y, np.ma.masked_invalid(Z))
    columns = []
    for level in levels:
        for line in gen.lines(float(level)):
            columns.append(np.array([[level], [len(line)]]))
            columns.append(np.asarray(line).T)
    return np.hstack(columns) if columns else np.zeros((2, 0))


def _quiver_scale(P, V, factor: float, counts) -> list[np.ndarray]:
    """
    Arrows scaled as MATLAB scales them: so that the longest, measured in
    grid spacings, is ``0.9 * factor`` of one. ``P`` are the start
    coordinates, ``V`` the components, ``counts`` the points along each axis.
    """
    if factor == 0:
        return list(V)
    spacing = sum(((np.nanmax(p) - np.nanmin(p)) / c) ** 2
                  for p, c in zip(P, counts) if p.size)
    length = np.sqrt(sum(v * v for v in V))
    longest = float(np.nanmax(length) / math.sqrt(spacing)) \
        if spacing > 0 and length.size else 0.0
    scale = factor * 0.9 / longest if longest > 0 else factor * 0.9
    return [v * scale for v in V]


def _image_matrix(C, who: str) -> np.ndarray:
    a = np.asarray(C)
    if a.dtype == bool:
        a = a.astype(float)
    if a.ndim > 2:
        raise MatlabError(f"{who}: true-colour (m×n×3) images need N-D "
                          f"arrays, which Evans does not have yet.")
    if np.iscomplexobj(a):
        a = a.real
    return _as2d(a.astype(float))


# ──────────────────────────────────────────────────────────────
#  The library
# ──────────────────────────────────────────────────────────────

class PlotLibrary:
    """Plotting: see the module's docstring."""

    # ── figures and axes ────────────────────────────────────────

    def _target(self, args):
        """
        Drop a leading axes or layout handle, making its axes current.
        Returns the remaining arguments and the handle (or None).
        """
        if args and isinstance(args[0], Graphic):
            handle = args[0]
            if handle.kind == "axes":
                self.rt.figures.select(handle)
            return tuple(args[1:]), handle
        return tuple(args), None

    def _axes(self, args) -> tuple[tuple, FigureSpec]:
        """The arguments without a handle, and the axes they act on."""
        args, _handle = self._target(args)
        return args, self.rt.figures.ensure()

    def f_close(self, *args):
        self.rt.figures = Figures()
        self.rt.figures.close_requested = True

    def f_clf(self, *_):
        figs = self.rt.figures
        if figs.figure() in figs.specs:
            figs.specs.remove(figs.figure())
        figs.new()

    def f_cla(self, *args):
        figs = self.rt.figures
        self._target(args)
        spec = figs.current
        if spec is not None:
            spec.traces.clear()
            spec.extra.clear()
            spec.title = spec.xlabel = spec.ylabel = ""

    @_nargout
    def f_figure(self, *_, nargout=0):
        figs = self.rt.figures
        figs.new()
        # A handle is the figure's number: the one its next plot will get.
        return len(figs.specs) + 1 if nargout else None

    @_nargout
    def f_gcf(self, nargout=1):
        figs = self.rt.figures
        current = figs.figure()
        return (figs.specs.index(current) + 1 if current in figs.specs
                else len(figs.specs) + 1)

    @_nargout
    def f_gca(self, nargout=1):
        return self.rt.figures.handle()

    @_nargout
    def f_subplot(self, m, n=None, p=None, *_, nargout=0):
        if n is None:                      # subplot(211)
            digits = str(int(m))
            if len(digits) != 3:
                raise MatlabError("subplot needs subplot(m, n, p).")
            m, n, p = (int(d) for d in digits)
        rows, cols = int(m), int(n)
        cells = tuple(sorted(int(c) for c in np.atleast_1d(p).reshape(-1)))
        if not cells or cells[0] < 1 or cells[-1] > rows * cols:
            raise MatlabError(f"Index exceeds number of subplots "
                              f"({rows * cols}).")
        self.rt.figures.subplot(rows, cols, cells)
        return self.rt.figures.handle() if nargout else None

    @_nargout
    def f_tiledlayout(self, *args, nargout=0):
        """``tiledlayout(m, n)``, or ``'flow'``, ``'horizontal'``, ``'vertical'``."""
        data, _props, flags = _options(args, ("flow", "horizontal",
                                              "vertical"))
        numbers = [d for d in data if not isinstance(d, str)]
        if len(numbers) >= 2:
            rows, cols = (int(_scalar_of(v)) for v in numbers[:2])
            if rows < 1 or cols < 1:
                raise MatlabError("tiledlayout needs at least one row and "
                                  "one column.")
            grid = self.rt.figures.tiled(rows, cols)
        else:
            mode = next(iter(flags), "flow")
            grid = self.rt.figures.tiled(0, 0, mode)
        return Graphic("layout", grid) if nargout else None

    @_nargout
    def f_nexttile(self, *args, nargout=0):
        """``nexttile``, ``nexttile(k)``, ``nexttile([r c])``, ``nexttile(k, [r c])``."""
        args, handle = self._target(args)
        if handle is not None and handle.kind == "layout":
            self.rt.figures.grid = handle.figure
        numbers = [a for a in args if not isinstance(a, str)]
        tile, span = None, (1, 1)
        for value in numbers:
            v = np.asarray(value, float).reshape(-1)
            if v.size == 2:
                span = (int(v[0]), int(v[1]))
            elif v.size == 1:
                tile = int(v[0])
        figs = self.rt.figures
        pane = figs.nexttile(tile, span)
        return Graphic("axes", figs.grid, pane) if nargout else None

    def f_sgtitle(self, *args):
        args, _handle = self._target(args)
        figs = self.rt.figures
        (figs.grid or figs.ensure()).title = _label_text(args[0])

    def f_hold(self, *args):
        args, _handle = self._target(args)
        state = args[0] if args else None
        figs = self.rt.figures
        figs.hold = (not figs.hold) if state is None else \
            str(state).lower() in ("on", "all")
        if figs.pane is not None:
            figs.pane["hold"] = figs.hold

    def f_grid(self, *args):
        args, _handle = self._target(args)
        figs = self.rt.figures
        if figs.current is not None:
            figs.current.extra["grid"] = (args[0] if args else "on")

    def f_yyaxis(self, *args):
        """``yyaxis left`` / ``yyaxis right``: which y axis plots go on."""
        args, spec = self._axes(args)
        side = str(args[0]).lower() if args else ""
        if side not in ("left", "right"):
            raise MatlabError("yyaxis needs 'left' or 'right'.")
        spec.extra["yyaxis"] = True
        spec.extra["side"] = side

    # ── line plots ──────────────────────────────────────────────

    def _xy(self, args, kind_extra: dict | None = None,
            style: str | None = None):
        args, _handle = self._target(args)
        spec = FigureSpec("xy", "", "", "")
        spec.extra.update(kind_extra or {})
        values, props, _flags = _options(args)
        label = props.pop("label", "")
        k = 0
        series = []
        while k < len(values):
            v = values[k]
            if isinstance(v, str):
                if series:
                    series[-1][2] = v
                k += 1
                continue
            nxt = values[k + 1] if k + 1 < len(values) else None
            if nxt is not None and not isinstance(nxt, str):
                series.append([v, nxt, ""])
                k += 2
            else:
                y = np.asarray(v)
                if np.iscomplexobj(y):
                    series.append([y.real, y.imag, ""])
                else:
                    n = y.shape[0] if y.ndim == 2 and y.shape[0] > 1 \
                        else y.size
                    series.append([np.arange(1, n + 1), y, ""])
                k += 1
        warned = False
        for x, y, linespec in series:
            x, y = np.asarray(x), np.asarray(y)
            if np.iscomplexobj(x) or np.iscomplexobj(y):
                if not warned:
                    print("Warning: Imaginary parts of complex X and/or Y "
                          "arguments ignored.")
                    warned = True
                x, y = x.real, y.real
            x = np.asarray(x, float)
            y = np.asarray(y, float)
            columns = [y] if y.ndim <= 1 or 1 in y.shape else (
                [y[:, c] for c in range(y.shape[1])]
                if y.shape[0] == x.size else [y[r] for r in range(y.shape[0])])
            for col in columns:
                xs, ys = x.reshape(-1), np.asarray(col).reshape(-1)
                kind = style or _style(linespec)
                if kind == "stairs":           # hold each value to the next x
                    xs, ys = np.repeat(xs, 2)[1:], np.repeat(ys, 2)[:-1]
                    kind = "line"
                spec.add(xs, ys, label, style=kind,
                         **_apply_linespec(props, linespec))
        self.rt.figures.collect(spec)

    def f_plot(self, *args):
        self._xy(args)

    def f_stem(self, *args):
        self._xy(args, style="stem")

    def f_stairs(self, *args):
        self._xy(args, style="stairs")

    def f_semilogx(self, *args):
        self._xy(args, {"logx": True})

    def f_semilogy(self, *args):
        self._xy(args, {"logy": True})

    def f_loglog(self, *args):
        self._xy(args, {"logx": True, "logy": True})

    def f_plot3(self, *args):
        """``plot3(x, y, z)``, with line specs; matrices are one line a column."""
        args, _handle = self._target(args)
        data, props, _flags = _options(args)
        label = props.pop("label", "")
        series, k = [], 0
        while k < len(data):
            if isinstance(data[k], str):
                if series:
                    series[-1][3] = data[k]
                k += 1
                continue
            if k + 2 >= len(data) or any(isinstance(d, str)
                                         for d in data[k:k + 3]):
                raise MatlabError("plot3 needs x, y and z.")
            series.append([*data[k:k + 3], ""])
            k += 3
        spec = FigureSpec("xy")
        for x, y, z, linespec in series:
            X, Y, Z = (_as2d(np.asarray(a, float)) for a in (x, y, z))
            if 1 in Z.shape:
                X, Y, Z = (a.reshape(-1, 1) for a in (X, Y, Z))
            X, Y = (np.broadcast_to(a.reshape(-1, 1) if 1 in a.shape else a,
                                    Z.shape) for a in (X, Y))
            style = "scatter3" if _style(linespec) == "scatter" else "line3"
            for c in range(Z.shape[1]):
                spec.add(X[:, c], Y[:, c], label, style, z=Z[:, c],
                         **_apply_linespec(props, linespec))
        self.rt.figures.collect(spec)

    # ── markers and bars ────────────────────────────────────────

    def _scatter(self, args, three: bool):
        who = "scatter3" if three else "scatter"
        args, _handle = self._target(args)
        data, props, flags = _options(args, ("filled",))
        label = props.pop("label", "")
        numbers = [d for d in data if not isinstance(d, str)]
        need = 3 if three else 2
        if len(numbers) < need:
            raise MatlabError(f"{who} needs {'x, y and z' if three else 'x and y'}.")
        x, y = _vector(numbers[0]), _vector(numbers[1])
        z = _vector(numbers[2]) if three else None
        rest = numbers[need:]
        if x.size != y.size or (three and z.size != x.size):
            raise MatlabError(f"{who}: the coordinates must have the same "
                              f"number of elements.")
        for text in (d for d in data if isinstance(d, str)):
            if text.lower() in _NAMES:
                props.setdefault("color", _colour(text, who))
                continue
            spec_props = _linespec(text)
            if "marker" in spec_props:
                props.setdefault("marker", spec_props["marker"])
            if "color" in spec_props:
                props.setdefault("color", spec_props["color"])
        props.setdefault("marker", "o")
        if rest and _numel(rest[0]):
            props["sizes"] = _vector(rest[0])
        if len(rest) > 1 and _numel(rest[1]):
            c = np.asarray(rest[1], float)
            if c.size == 3 and x.size != 3:
                props["color"] = _colour(c, who)
            elif c.ndim == 2 and c.shape[1] == 3 and c.shape[0] == x.size:
                props["colors"] = [_colour(row, who) for row in c]
            else:
                props["cdata"] = c.reshape(-1)
        elif len(rest) > 1 and isinstance(rest[1], str):
            props["color"] = _colour(rest[1], who)
        if "filled" in flags:
            props["filled"] = True
        spec = FigureSpec("xy")
        spec.add(x, y, label, "scatter3" if three else "scatter", z=z,
                 **props)
        self.rt.figures.collect(spec)

    def f_scatter(self, *args):
        """``scatter(x, y, sz, c, 'filled')``: markers sized and coloured."""
        self._scatter(args, three=False)

    def f_scatter3(self, *args):
        self._scatter(args, three=True)

    def f_errorbar(self, *args):
        """
        ``errorbar(y, err)``, ``errorbar(x, y, err)``,
        ``errorbar(x, y, neg, pos)``, ``errorbar(x, y, yneg, ypos, xneg,
        xpos)``, with ``'horizontal'`` or ``'both'``.
        """
        args, _handle = self._target(args)
        data, props, flags = _options(args, ("horizontal", "vertical",
                                             "both"))
        label = props.pop("label", "")
        numbers = [d for d in data if not isinstance(d, str)]
        linespec = next((d for d in data if isinstance(d, str)), "")
        if len(numbers) == 2:
            y, err = numbers
            x = np.arange(1.0, _numel(y) + 1)
            bars = [err]
        elif len(numbers) >= 3:
            x, y, *bars = numbers
        else:
            raise MatlabError("errorbar needs y and the error.")
        x, y = _vector(x), _vector(y)
        bars = [np.broadcast_to(_vector(b), y.shape) if _numel(b) else None
                for b in bars]
        if len(bars) >= 4:
            yneg, ypos, xneg, xpos = bars[:4]
        else:
            neg, pos = (bars[0], bars[0]) if len(bars) == 1 else bars[:2]
            yneg = ypos = xneg = xpos = None
            if "horizontal" in flags or "both" in flags:
                xneg, xpos = neg, pos
            if "horizontal" not in flags:
                yneg, ypos = neg, pos
        bar_props = {k: np.asarray(v, float) for k, v in
                     (("yneg", yneg), ("ypos", ypos), ("xneg", xneg),
                      ("xpos", xpos)) if v is not None}
        style = "errorbar"
        line = _apply_linespec(props, linespec)
        if linespec and "linestyle" not in line and "marker" in line:
            line["linestyle"] = None
        spec = FigureSpec("xy")
        spec.add(x, y, label, style, **bar_props, **line)
        self.rt.figures.collect(spec)

    def f_bar(self, *args):
        """
        Bars, ``bar(y)`` or ``bar(x, y[, width])``; a matrix's columns are
        drawn as groups of bars side by side, or on top of each other with
        ``'stacked'``.
        """
        self._bars(args, horizontal=False)

    def f_barh(self, *args):
        self._bars(args, horizontal=True)

    def _bars(self, args, horizontal: bool):
        args, _handle = self._target(args)
        data, props, flags = _options(args, ("stacked", "grouped"))
        label = props.pop("label", "")
        for text in (d for d in data if isinstance(d, str)):
            props.setdefault("color", _linespec(text).get("color"))
        props = {k: v for k, v in props.items() if v is not None}
        numbers = [a for a in data if not isinstance(a, str)]
        if len(numbers) == 1:
            y = _as2d(numbers[0])
            x = None
        else:
            x, y = numbers[0], _as2d(numbers[1])
        y = y.T if y.shape[0] == 1 else y
        x = np.arange(1.0, y.shape[0] + 1) if x is None else \
            np.asarray(x, float).reshape(-1)
        width = float(_scalar_of(numbers[2])) if len(numbers) > 2 else 0.8
        step = float(np.min(np.diff(np.sort(x)))) if x.size > 1 else 1.0
        groups = y.shape[1]
        stacked = "stacked" in flags
        spec = FigureSpec("xy")
        spec.extra["bar_width"] = width * step / (1 if stacked else groups)
        base = np.zeros(y.shape[0])
        extra = {"horizontal": True} if horizontal else {}
        for k in range(groups):
            values = np.real(y[:, k]).astype(float)
            if stacked:
                spec.add(x, base + values, label, style="bar", base=base.copy(),
                         **extra, **props)
                base = base + values
            else:
                offset = (k - (groups - 1) / 2) * width * step / groups
                spec.add(x + offset, values, label, style="bar", **extra,
                         **props)
        self.rt.figures.collect(spec)

    @_nargout
    def f_histogram(self, x, bins=None, *_, nargout=1):
        """Counts in bins drawn as bars; returns Values and BinEdges."""
        data = np.asarray(x, float).reshape(-1)
        data = data[np.isfinite(data)]
        edges = _mr._bin_edges(data, bins)
        counts, _edges = np.histogram(data, bins=edges)
        centres = (edges[:-1] + edges[1:]) / 2
        spec = FigureSpec("xy")
        spec.extra["bar_width"] = float(np.min(np.diff(edges))) if \
            edges.size > 1 else 1.0
        spec.add(centres, counts, style="bar")
        self.rt.figures.collect(spec)
        return Struct(Values=counts.astype(float), BinEdges=edges,
                      NumBins=int(counts.size),
                      BinWidth=float(spec.extra["bar_width"]),
                      Data=data) if nargout else None

    @_nargout
    def f_histcounts(self, x, bins=None, *_, nargout=1):
        data = np.asarray(x, float).reshape(-1)
        data = data[np.isfinite(data)]
        edges = _mr._bin_edges(data, bins)
        counts = np.histogram(data, bins=edges)[0].astype(float)
        return (counts, edges)[:nargout] if nargout >= 2 else counts

    @_nargout
    def f_hist(self, y, bins=10, *_, nargout=1):
        """The old ``hist``: equal bins over the data's range, by centre."""
        data = np.asarray(y, float).reshape(-1)
        if _numel(bins) > 1:
            centres = np.asarray(bins, float).reshape(-1)
            mids = (centres[:-1] + centres[1:]) / 2
            edges = np.concatenate([[-np.inf], mids, [np.inf]])
        else:
            lo, hi = (float(np.min(data)), float(np.max(data))) \
                if data.size else (0.0, 1.0)
            if lo == hi:
                lo, hi = lo - 0.5, hi + 0.5
            edges = np.linspace(lo, hi, int(_scalar_of(bins)) + 1)
            centres = (edges[:-1] + edges[1:]) / 2
            edges[0], edges[-1] = -np.inf, np.inf
        counts = np.histogram(data, bins=edges)[0].astype(float)
        if nargout == 0:
            self._xy((centres, counts), style="bar")
            self.rt.figures.current.extra["bar_width"] = float(
                np.min(np.diff(centres))) if centres.size > 1 else 1.0
            return None
        return (counts, centres)[:nargout] if nargout >= 2 else counts

    # ── areas, polygons, pies ───────────────────────────────────

    def f_area(self, *args):
        """``area(y)``, ``area(x, Y)``, ``area(..., basevalue)``: stacked columns."""
        args, _handle = self._target(args)
        data, props, _flags = _options(args)
        label = props.pop("label", "")
        numbers = [d for d in data if not isinstance(d, str)]
        if not numbers:
            raise MatlabError("area needs the values to fill under.")
        if len(numbers) == 1 or (len(numbers) == 2 and _numel(numbers[1]) == 1
                                 and _numel(numbers[0]) > 1):
            Y, x = _as2d(np.asarray(numbers[0], float)), None
            base = numbers[1] if len(numbers) == 2 else None
        else:
            x, Y = numbers[0], _as2d(np.asarray(numbers[1], float))
            base = numbers[2] if len(numbers) > 2 else None
        if Y.shape[0] == 1:
            Y = Y.T
        x = np.arange(1.0, Y.shape[0] + 1) if x is None else _vector(x)
        if x.size != Y.shape[0]:
            raise MatlabError("area: x must have one value per row of Y.")
        lower = np.full(Y.shape[0], float(_scalar_of(base)) if base is not None
                        else props.pop("base", 0.0))
        props.pop("base", None)
        spec = FigureSpec("xy")
        for k in range(Y.shape[1]):
            upper = lower + Y[:, k]
            spec.add(x, upper, label, "area", base=lower.copy(), **props)
            lower = upper
        self.rt.figures.collect(spec)

    def _polygons(self, args, who: str, add: bool):
        args, _handle = self._target(args)
        data, props, _flags = _options(args)
        label = props.pop("label", "")
        spec = FigureSpec("xy")
        if "faces" in props and "vertices" in props:
            V = _as2d(props.pop("vertices"))
            F = _as2d(props.pop("faces"))
            for face in F:
                idx = face[np.isfinite(face)].astype(int) - 1
                self._polygon(spec, V[idx, 0], V[idx, 1],
                              V[idx, 2] if V.shape[1] > 2 else None,
                              props.get("color"), props, label, who)
        elif "xdata" in props:
            X = _as2d(props.pop("xdata"))
            Y = _as2d(props.pop("ydata", np.zeros_like(X)))
            Z = props.pop("zdata", None)
            self._polygon_columns(spec, X, Y, Z, props.get("color"), props,
                                  label, who)
        else:
            k = 0
            while k < len(data):
                three = who == "fill3"
                group = data[k:k + (4 if three else 3)]
                if len(group) < (4 if three else 3):
                    raise MatlabError(f"{who} needs x, y{', z' if three else ''}"
                                      f" and a colour.")
                X, Y = _as2d(np.asarray(group[0], float)), \
                    _as2d(np.asarray(group[1], float))
                Z = group[2] if three else None
                self._polygon_columns(spec, X, Y, Z, group[-1], props, label,
                                      who)
                k += len(group)
        self.rt.figures.collect(spec, add=add)

    def _polygon_columns(self, spec, X, Y, Z, colour, props, label, who):
        if X.shape[0] == 1:
            X, Y = X.T, Y.T
            Z = None if Z is None else _as2d(np.asarray(Z, float)).T
        elif Z is not None:
            Z = _as2d(np.asarray(Z, float))
        for c in range(X.shape[1]):
            colour_c = colour
            if not isinstance(colour, (str, type(None))) and \
                    _numel(colour) == X.shape[1] and _numel(colour) != 3:
                colour_c = np.asarray(colour, float).reshape(-1)[c]
            self._polygon(spec, X[:, c], Y[:, c],
                          None if Z is None else Z[:, c], colour_c, props,
                          label, who)

    @staticmethod
    def _polygon(spec, x, y, z, colour, props, label, who):
        trace_props = {k: v for k, v in props.items() if k != "color"}
        if isinstance(colour, str) and colour.lower() in ("flat", "interp",
                                                          "none"):
            trace_props["color"] = colour.lower()
        elif isinstance(colour, str) or (colour is not None
                                         and _numel(colour) == 3):
            trace_props["color"] = _colour(colour, who)
        elif colour is not None:
            trace_props["cdata"] = np.asarray(colour, float).reshape(-1)
        trace_props.setdefault("edgecolor", "#000000")
        spec.add(x, y, label, "fill3" if z is not None else "fill",
                 z=z, **trace_props)

    def f_fill(self, *args):
        """``fill(x, y, c)``: filled polygons; each column of x and y is one."""
        self._polygons(args, "fill", add=False)

    def f_fill3(self, *args):
        self._polygons(args, "fill3", add=False)

    def f_patch(self, *args):
        """
        ``patch(x, y, c)``, or by ``'XData'``/``'YData'`` or
        ``'Faces'``/``'Vertices'``: polygons, always added to the axes.
        """
        lead = list(args[:4])
        if len(lead) == 4 and not any(isinstance(a, str) for a in lead) \
                and _numel(lead[2]) == _numel(lead[0]) > 1:
            self._polygons(args, "fill3", add=True)   # patch(x, y, z, c)
        else:
            self._polygons(args, "patch", add=True)

    def f_pie(self, *args):
        """``pie(x)``, ``pie(x, explode)``, ``pie(x, labels)``, ``pie(x, explode, labels)``."""
        args, _handle = self._target(args)
        if not args:
            raise MatlabError("pie needs the values.")
        x = _vector(args[0])
        if np.any(x < 0):
            raise MatlabError("pie: the values must not be negative.")
        explode, labels = None, None
        for a in args[1:]:
            if isinstance(a, Cell) or isinstance(a, str):
                labels = [str(v) for v in a] if isinstance(a, Cell) else [a]
            else:
                explode = np.broadcast_to(_vector(a) != 0, x.shape).copy()
        total = float(x.sum())
        fractions = x / total if total > 1 or total == 0 else x
        if labels is None:
            labels = [("< 1%" if 0 < f < 0.005 else f"{round(100 * f)}%")
                      for f in fractions]
        if len(labels) != x.size:
            raise MatlabError("pie: give one label per value.")
        spec = FigureSpec("pie")
        spec.add(np.arange(x.size), fractions, "", "pie", labels=labels,
                 explode=explode if explode is not None
                 else np.zeros(x.size, bool))
        self.rt.figures.collect(spec)

    # ── fields: arrows, contours, surfaces ──────────────────────

    def _field(self, args, three: bool):
        who = "quiver3" if three else "quiver"
        args, _handle = self._target(args)
        data, props, flags = _options(args, ("off",))
        label = props.pop("label", "")
        linespec = next((d for d in data if isinstance(d, str)), "")
        numbers = [d for d in data if not isinstance(d, str)]
        parts = 3 if three else 2
        if len(numbers) in (parts, parts + 1):
            V = [_as2d(np.asarray(a, float)) for a in numbers[:parts]]
            rows, cols = V[0].shape
            grid = list(np.meshgrid(np.arange(1.0, cols + 1),
                                    np.arange(1.0, rows + 1)))
            P = grid + ([np.zeros_like(V[0])] if three else [])
            rest = numbers[parts:]
        elif len(numbers) in (2 * parts, 2 * parts + 1):
            P = [_as2d(np.asarray(a, float)) for a in numbers[:parts]]
            V = [_as2d(np.asarray(a, float)) for a in numbers[parts:2 * parts]]
            rest = numbers[2 * parts:]
            if P[0].size != V[0].size and 1 in P[0].shape:
                grid = np.meshgrid(P[0].reshape(-1), P[1].reshape(-1))
                P = list(grid) + P[2:]
        else:
            raise MatlabError(f"{who} needs the arrows' components, and "
                              f"optionally where they start.")
        if any(p.size != V[0].size for p in P + V):
            raise MatlabError(f"{who}: the positions and components must "
                              f"have the same number of elements.")
        if three or 1 in V[0].shape:
            counts = [V[0].size ** (1 / parts)] * parts
        else:
            counts = [V[0].shape[1], V[0].shape[0]]
        autoscale = props.pop("autoscale", True)
        scale = props.pop("scale", 1.0)
        factor = 0.0 if "off" in flags or not autoscale else (
            float(_scalar_of(rest[0])) if rest else scale)
        P = [p.reshape(-1) for p in P]
        V = [v.reshape(-1) for v in V]
        components = _quiver_scale(P, V, factor, counts)
        line = _apply_linespec(props, linespec)
        spec = FigureSpec("xy")
        keys = ("u", "v", "w")
        spec.add(P[0], P[1], label, who, z=P[2] if three else None,
                 **{keys[i]: components[i] for i in range(parts)}, **line)
        self.rt.figures.collect(spec)

    def f_quiver(self, *args):
        """``quiver(x, y, u, v)``, ``quiver(u, v)``, ``quiver(..., scale)``."""
        self._field(args, three=False)

    def f_quiver3(self, *args):
        self._field(args, three=True)

    def _contour(self, args, style: str, nargout: int):
        args, _handle = self._target(args)
        data, props, _flags = _options(args)
        label = props.pop("label", "")
        linespec = next((d for d in data if isinstance(d, str)), "")
        numbers = [d for d in data if not isinstance(d, str)]
        if len(numbers) in (1, 2):
            X = Y = None
            Z = numbers[0]
            given = numbers[1] if len(numbers) == 2 else None
        elif len(numbers) in (3, 4):
            X, Y, Z = numbers[:3]
            given = numbers[3] if len(numbers) == 4 else None
        else:
            raise MatlabError(f"{style} needs Z, or X, Y and Z.")
        X, Y, Z = _grid(X, Y, Z, style)
        finite = Z[np.isfinite(Z)]
        lo, hi = (float(finite.min()), float(finite.max())) if finite.size \
            else (0.0, 1.0)
        if "levels" in props:
            levels = np.unique(props.pop("levels").reshape(-1))
        elif given is not None and _numel(given) == 1:
            levels = _nice_levels(lo, hi, int(_scalar_of(given)))
        elif given is not None:
            levels = np.unique(np.asarray(given, float).reshape(-1))
        else:
            levels = _nice_levels(lo, hi)
        line = _apply_linespec(props, linespec)
        spec = FigureSpec("xy")
        spec.add(X, Y, label, style, z=Z, levels=levels, zrange=(lo, hi),
                 **line)
        self.rt.figures.collect(spec)
        if nargout:
            return _contour_matrix(X, Y, Z, levels)
        return None

    @_nargout
    def f_contour(self, *args, nargout=0):
        """``contour(Z)``, ``contour(X, Y, Z)``, ``contour(..., n)`` or ``levels``."""
        return self._contour(args, "contour", nargout)

    @_nargout
    def f_contourf(self, *args, nargout=0):
        return self._contour(args, "contourf", nargout)

    def _surface(self, args, style: str):
        args, _handle = self._target(args)
        data, props, _flags = _options(args)
        label = props.pop("label", "")
        numbers = [d for d in data if not isinstance(d, str)]
        if len(numbers) in (1, 2):
            X = Y = None
            Z = numbers[0]
            C = numbers[1] if len(numbers) == 2 else None
        elif len(numbers) in (3, 4):
            X, Y, Z = numbers[:3]
            C = numbers[3] if len(numbers) == 4 else None
        else:
            raise MatlabError(f"{style} needs Z, or X, Y and Z.")
        X, Y, Z = _grid(X, Y, Z, style)
        if C is not None:
            C = _as2d(np.asarray(C, float))
            if C.shape != Z.shape:
                raise MatlabError(f"{style}: C must be the size of Z.")
            props["cdata"] = C
        spec = FigureSpec("xy")
        spec.add(X, Y, label, "surface" if style.startswith("surf")
                 else "mesh", z=Z, **props)
        if style in ("surfc", "meshc"):
            finite = Z[np.isfinite(Z)]
            lo, hi = (float(finite.min()), float(finite.max())) \
                if finite.size else (0.0, 1.0)
            spec.add(X, Y, "", "contour3", z=Z, levels=_nice_levels(lo, hi),
                     zrange=(lo, hi), base=lo)
        self.rt.figures.collect(spec)

    def f_surf(self, *args):
        """``surf(Z)``, ``surf(X, Y, Z)``, ``surf(X, Y, Z, C)``: a shaded surface."""
        self._surface(args, "surf")

    def f_mesh(self, *args):
        self._surface(args, "mesh")

    def f_surfc(self, *args):
        self._surface(args, "surfc")

    def f_meshc(self, *args):
        self._surface(args, "meshc")

    def f_shading(self, *args):
        """``shading flat``, ``shading interp`` or ``shading faceted``."""
        args, spec = self._axes(args)
        mode = str(args[0]).lower() if args else ""
        if mode not in ("flat", "interp", "faceted"):
            raise MatlabError("shading needs 'flat', 'interp' or 'faceted'.")
        for trace in spec.traces:
            if trace.style in ("surface", "mesh", "fill", "fill3"):
                trace.props["shading"] = mode

    @_nargout
    def f_view(self, *args, nargout=0):
        """``view(az, el)``, ``view([az el])``, ``view(2)``, ``view(3)``."""
        args, spec = self._axes(args)
        values = np.concatenate([np.asarray(a, float).reshape(-1)
                                 for a in args]) if args else np.array([])
        if values.size == 1:
            if values[0] == 2:
                spec.extra["view"] = (0.0, 90.0)
            elif values[0] == 3:
                spec.extra["view"] = (-37.5, 30.0)
            else:
                raise MatlabError("view(n) takes 2 or 3.")
        elif values.size == 2:
            spec.extra["view"] = (float(values[0]), float(values[1]))
        elif values.size:
            raise MatlabError("view needs the azimuth and elevation.")
        if nargout:
            az, el = spec.extra.get("view") or ((-37.5, 30.0) if spec.is_3d
                                                else (0.0, 90.0))
            return (az, el) if nargout >= 2 else np.array([az, el])
        return None

    @_nargout
    def f_peaks(self, n=49, y=None, nargout=1):
        """MATLAB's demonstration surface, on an n×n grid over [-3, 3]."""
        if y is None:
            v = np.asarray(n, float).reshape(-1)
            v = np.linspace(-3, 3, int(v[0])) if v.size == 1 else v
            X, Y = np.meshgrid(v, v)
        else:
            X, Y = np.asarray(n, float), np.asarray(y, float)
        Z = (3 * (1 - X) ** 2 * np.exp(-X ** 2 - (Y + 1) ** 2)
             - 10 * (X / 5 - X ** 3 - Y ** 5) * np.exp(-X ** 2 - Y ** 2)
             - np.exp(-(X + 1) ** 2 - Y ** 2) / 3)
        if nargout >= 2:
            return tuple(_normalise(a) for a in (X, Y, Z))[:nargout]
        if nargout == 0 and y is None:
            self.f_surf(X, Y, Z)
            return None
        return _normalise(Z)

    # ── images and colour ───────────────────────────────────────

    def _image(self, args, who: str):
        args, _handle = self._target(args)
        data, props, _flags = _options(args)
        numbers = [d for d in data if not isinstance(d, str)]
        if not numbers:
            raise MatlabError(f"{who} needs the image data.")
        if len(numbers) >= 3:
            x, y, C, rest = numbers[0], numbers[1], numbers[2], numbers[3:]
        else:
            x = y = None
            C, rest = numbers[0], numbers[1:]
        raw_dtype = np.asarray(C).dtype
        C = _image_matrix(C, who)
        rows, cols = C.shape
        xr = [1.0, float(cols)] if x is None else _vector(x)[[0, -1]]
        yr = [1.0, float(rows)] if y is None else _vector(y)[[0, -1]]
        spec = FigureSpec("xy")
        figs = self.rt.figures
        cur = figs.current
        fresh = cur is None or not figs.hold or not cur.traces
        extra = {}
        if who == "imshow":
            extra.update(aspect="equal", axis_off=True, tight=True)
            if rest and _numel(rest[0]) and np.asarray(rest[0]).ndim == 2 \
                    and np.asarray(rest[0]).shape[-1] == 3 \
                    and np.asarray(rest[0]).shape[0] > 1:
                extra["colormap"] = np.asarray(rest[0], float)
                props["direct"] = True
            else:
                extra["colormap"] = _colormap("gray")
                if rest and _numel(rest[0]) == 0:
                    finite = C[np.isfinite(C)]
                    extra["clim"] = (float(finite.min()), float(finite.max())) \
                        if finite.size else (0.0, 1.0)
                elif rest:
                    lims = _vector(rest[0])
                    extra["clim"] = (float(lims[0]), float(lims[1]))
                else:
                    # An integer image spans its type's range: uint8 is 0–255.
                    extra["clim"] = ((float(np.iinfo(raw_dtype).min),
                                      float(np.iinfo(raw_dtype).max))
                                     if raw_dtype.kind in "iu"
                                     else (0.0, 1.0))
        elif who == "imagesc" and rest:
            lims = _vector(rest[0])
            if lims.size != 2 or lims[0] >= lims[1]:
                raise MatlabError("imagesc: the colour limits are [low high] "
                                  "with low < high.")
            extra["clim"] = (float(lims[0]), float(lims[1]))
        elif who == "image":
            props["direct"] = True
        if fresh:
            extra.setdefault("tight", True)
            extra["ydir"] = "reverse"
        spec.extra.update(extra)
        spec.add(xr, yr, "", "image", z=C, **props)
        figs.collect(spec)

    def f_imagesc(self, *args):
        """``imagesc(C)``, ``imagesc(x, y, C)``, ``imagesc(..., [lo hi])``."""
        self._image(args, "imagesc")

    def f_image(self, *args):
        self._image(args, "image")

    def f_imshow(self, *args):
        self._image(args, "imshow")

    @_nargout
    def f_colormap(self, *args, nargout=0):
        """``colormap(name)``, ``colormap(map)``; ``cmap = colormap`` reads it."""
        args, _handle = self._target(args)
        figs = self.rt.figures
        if args:
            value = args[0]
            if isinstance(value, str):
                cmap = _colormap(value, int(_scalar_of(args[1])) if len(args) > 1
                                 else 256)
            else:
                cmap = _as2d(np.asarray(value, float))
                if cmap.shape[1] != 3 or cmap.min() < 0 or cmap.max() > 1:
                    raise MatlabError("colormap: a map is an n-by-3 matrix of "
                                      "RGB values between 0 and 1.")
            figs.colormap = cmap
            for spec in self._figure_axes():
                spec.extra["colormap"] = cmap
        if nargout:
            spec = figs.current
            cmap = (spec.extra.get("colormap") if spec is not None else None)
            return cmap if cmap is not None else (
                figs.colormap if figs.colormap is not None
                else _colormap("parula"))
        return None

    def _figure_axes(self) -> list[FigureSpec]:
        """Every axes in the current figure, made if there are none."""
        figs = self.rt.figures
        grid = figs.grid
        if grid is not None:
            specs = [p["spec"] for p in grid.extra["panes"]
                     if p["spec"] is not None]
            figs.touch()
            return specs or [figs.ensure()]
        return [figs.ensure()]

    @_nargout
    def f_colorbar(self, *args, nargout=0):
        """``colorbar``, ``colorbar('off')``, ``colorbar(location)``."""
        args, spec = self._axes(args)
        word = "eastoutside"
        if args and isinstance(args[0], str) and args[0].lower() not in _PROPS:
            word, args = args[0].lower(), args[1:]
        _data, props, _flags = _options(args)
        word = props.get("location", word)
        if word in ("off", "delete", "hide"):
            spec.extra.pop("colorbar", None)
        else:
            spec.extra["colorbar"] = {"location": word,
                                      "label": props.get("label", "")}
        return Graphic("axes", spec) if nargout else None

    @_nargout
    def f_caxis(self, *args, nargout=0):
        """``caxis([lo hi])`` (or ``clim``): the data range the colour map spans."""
        args, spec = self._axes(args)
        if args and isinstance(args[0], str):
            if args[0].lower() == "auto":
                spec.extra.pop("clim", None)
        elif args:
            lims = _vector(args[0])
            if lims.size != 2 or lims[0] >= lims[1]:
                raise MatlabError("The colour limits are [low high] with "
                                  "low < high.")
            spec.extra["clim"] = (float(lims[0]), float(lims[1]))
        if nargout:
            if "clim" in spec.extra:
                return np.array(spec.extra["clim"])
            values = [t.z if t.z is not None else t.props.get("cdata")
                      for t in spec.traces]
            values = [np.asarray(v).reshape(-1) for v in values
                      if v is not None]
            data = np.concatenate(values) if values else np.array([0.0, 1.0])
            data = data[np.isfinite(data)]
            return np.array([data.min(), data.max()]) if data.size else \
                np.array([0.0, 1.0])
        return None

    f_clim = f_caxis

    @_nargout
    def f_colororder(self, *args, nargout=0):
        """``colororder(C)``: the colours lines take in turn, figure-wide."""
        args, _handle = self._target(args)
        figs = self.rt.figures
        if args:
            value = args[0]
            if isinstance(value, str) and value.lower() == "default":
                order = None
            elif isinstance(value, str) and value.lower() == "gem":
                order = [_hex(row) for row in GEM]
            elif isinstance(value, str):
                order = [_colour(value, "colororder")]
            elif isinstance(value, Cell):
                order = [_colour(v, "colororder") for v in value]
            else:
                C = _as2d(np.asarray(value, float))
                if C.shape[1] != 3:
                    raise MatlabError("colororder: an n-by-3 matrix of RGB "
                                      "values, or a list of colour names.")
                order = [_colour(row, "colororder") for row in C]
            figs.colororder = order
            for spec in self._figure_axes():
                if order is None:
                    spec.extra.pop("colororder", None)
                else:
                    spec.extra["colororder"] = list(order)
        if nargout:
            order = figs.colororder
            if order is None:
                return GEM.copy()
            return np.array([[int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
                             for h in order])
        return None

    # ── annotation ──────────────────────────────────────────────

    def f_title(self, *args):
        args, handle = self._target(args)
        if handle is not None and handle.kind == "layout":
            handle.figure.title = _label_text(args[0])
            self.rt.figures.touch(handle.figure)
            return
        self.rt.figures.ensure().title = _as_text(args[0]) if not isinstance(
            args[0], Cell) else " ".join(args[0])

    def f_subtitle(self, *args):
        args, spec = self._axes(args)
        spec.extra["subtitle"] = _label_text(args[0])

    def _axis_label(self, axis: str, args):
        args, handle = self._target(args)
        text = _label_text(args[0])
        if handle is not None and handle.kind == "layout":
            handle.figure.extra[axis + "label"] = text
            self.rt.figures.touch(handle.figure)
            return
        spec = self.rt.figures.ensure()
        if axis == "y" and spec.extra.get("side") == "right":
            spec.extra.setdefault("right", {})["ylabel"] = text
        elif axis == "z":
            spec.extra["zlabel"] = text
        else:
            setattr(spec, axis + "label", text)

    def f_xlabel(self, *args):
        self._axis_label("x", args)

    def f_ylabel(self, *args):
        self._axis_label("y", args)

    def f_zlabel(self, *args):
        self._axis_label("z", args)

    def f_legend(self, *args):
        args, _handle = self._target(args)
        labels: list[str] = []
        k = 0
        location = None
        off = False
        while k < len(args):
            a = args[k]
            if isinstance(a, Cell):
                labels.extend(str(x) for x in a)
            elif isinstance(a, str):
                low = a.lower()
                if low in ("location", "orientation", "box", "fontsize",
                           "numcolumns", "interpreter", "autoupdate",
                           "textcolor", "color", "edgecolor"):
                    if low == "location" and k + 1 < len(args):
                        location = str(args[k + 1]).lower()
                    k += 2
                    continue
                if low in ("off", "hide"):
                    off = True
                elif low not in ("show", "boxoff", "boxon", "toggle"):
                    labels.append(a)
            k += 1
        spec = self.rt.figures.current
        if spec is None:
            return None
        if off:
            spec.extra["legend"] = "off"
        elif location is not None or labels:
            spec.extra.pop("legend", None)
        if location is not None:
            spec.extra["legend_location"] = location
        if not labels:
            return None
        named = [t for t in spec.traces if t.label] or spec.traces
        for trace, label in zip(named, labels):
            trace.label = label
        for k, entry in enumerate(spec.extra.get("phase", [])):
            if k < len(labels):
                spec.extra["phase"][k] = (entry[0], entry[1], labels[k])
        return None

    @_nargout
    def f_axis(self, *args, nargout=0):
        """
        ``axis([xmin xmax ymin ymax])`` (and ``zmin zmax``), and the modes:
        ``equal``, ``image``, ``square``, ``tight``, ``ij``, ``xy``, ``off``,
        ``on``, ``auto``, ``normal``.
        """
        args, spec = self._axes(args)
        for a in args:
            if isinstance(a, str):
                word = a.lower()
                if word in ("equal", "image", "square"):
                    spec.extra["aspect"] = "equal"
                    if word == "image":
                        spec.extra["tight"] = True
                elif word == "normal":
                    spec.extra.pop("aspect", None)
                elif word == "tight":
                    spec.extra["tight"] = True
                elif word == "ij":
                    spec.extra["ydir"] = "reverse"
                elif word == "xy":
                    spec.extra.pop("ydir", None)
                elif word == "off":
                    spec.extra["axis_off"] = True
                elif word == "on":
                    spec.extra.pop("axis_off", None)
                elif word in ("auto", "manual", "fill"):
                    for key in ("xlim", "ylim", "zlim", "tight"):
                        spec.extra.pop(key, None)
                elif word not in ("vis3d", "padded", "tickaligned"):
                    raise MatlabError(f"axis: unknown option '{a}'.")
            else:
                lims = np.asarray(a, float).reshape(-1)
                if lims.size not in (4, 6):
                    raise MatlabError("axis needs [xmin xmax ymin ymax] or "
                                      "six limits.")
                spec.extra["xlim"] = (lims[0], lims[1])
                spec.extra["ylim"] = (lims[2], lims[3])
                if lims.size == 6:
                    spec.extra["zlim"] = (lims[4], lims[5])
        if nargout:
            return np.array(self._limits(spec))
        return None

    @staticmethod
    def _limits(spec: FigureSpec) -> list[float]:
        """The axes' limits as set, else the data's range."""
        out = []
        for axis in ("x", "y") + (("z",) if spec.is_3d else ()):
            if spec.extra.get(axis + "lim") is not None:
                out += [float(v) for v in spec.extra[axis + "lim"]]
                continue
            arrays = [getattr(t, axis) for t in spec.traces
                      if getattr(t, axis) is not None]
            data = np.concatenate([np.asarray(a, float).reshape(-1)
                                   for a in arrays]) if arrays else \
                np.array([0.0, 1.0])
            data = data[np.isfinite(data)]
            out += [float(data.min()), float(data.max())] if data.size \
                else [0.0, 1.0]
        return out

    def _lim(self, axis: str, args, nargout: int):
        args, spec = self._axes(args)
        key = axis + "lim"
        target = spec.extra
        if axis == "y" and spec.extra.get("side") == "right":
            target = spec.extra.setdefault("right", {})
        if args and not isinstance(args[0], str):
            lims = np.asarray(args[0], float).reshape(-1)
            if lims.size != 2:
                raise MatlabError(f"{key} needs [min max].")
            target[key] = (lims[0], lims[1])
        elif args and args[0].lower() == "auto":
            target.pop(key, None)
        if nargout:
            limits = self._limits(spec)
            i = "xyz".index(axis) * 2
            return np.array(target.get(key) or limits[i:i + 2])
        return None

    @_nargout
    def f_xlim(self, *args, nargout=0):
        return self._lim("x", args, nargout)

    @_nargout
    def f_ylim(self, *args, nargout=0):
        return self._lim("y", args, nargout)

    @_nargout
    def f_zlim(self, *args, nargout=0):
        return self._lim("z", args, nargout)

    def f_text(self, *args):
        """``text(x, y, txt)`` or ``text(x, y, z, txt)``, with name–value pairs."""
        args, spec = self._axes(args)
        at = next((i for i, a in enumerate(args)
                   if isinstance(a, (str, Cell))), None)
        if at is None or at not in (2, 3):
            raise MatlabError("text needs x, y (and z) and the text.")
        _data, props, _flags = _options(args[at + 1:])
        coords = [_vector(a) for a in args[:at]]
        strings = [str(v) for v in args[at]] if isinstance(args[at], Cell) \
            else [args[at]]
        n = coords[0].size
        if len(strings) == 1:
            strings = strings * n
        if len(strings) != n or any(c.size != n for c in coords):
            raise MatlabError("text: give one string per point.")
        texts = spec.extra.setdefault("texts", [])
        for i in range(n):
            entry = {"x": float(coords[0][i]), "y": float(coords[1][i]),
                     "string": strings[i]}
            if at == 3:
                entry["z"] = float(coords[2][i])
            entry.update({k: props[k] for k in ("color", "fontsize", "halign",
                                                "valign", "rotation",
                                                "fontweight", "background")
                          if k in props})
            texts.append(entry)

    def _refline(self, axis: str, args):
        args, spec = self._axes(args)
        if not args:
            raise MatlabError(f"{axis}line needs where to draw the line.")
        values = _vector(args[0])
        rest = args[1:]
        linespec = rest[0] if rest and isinstance(rest[0], str) and \
            _is_linespec(rest[0]) else ""
        if linespec:
            rest = rest[1:]
        labels: list[str] = []
        if rest and (isinstance(rest[0], Cell) or (
                isinstance(rest[0], str) and rest[0].lower() not in _PROPS)):
            labels = [str(v) for v in rest[0]] if isinstance(rest[0], Cell) \
                else [rest[0]]
            rest = rest[1:]
        _data, props, _flags = _options(rest)
        line = _apply_linespec(props, linespec)
        if len(labels) == 1:
            labels *= values.size
        lines = spec.extra.setdefault(axis + "lines", [])
        for i, value in enumerate(values):
            entry = {"value": float(value),
                     "label": labels[i] if i < len(labels) else
                     props.get("label", "")}
            entry.update({k: line[k] for k in ("color", "linestyle",
                                               "linewidth") if k in line})
            lines.append(entry)

    def f_xline(self, *args):
        """``xline(x)``, ``xline(x, linespec, label)``: a vertical line across the axes."""
        self._refline("x", args)

    def f_yline(self, *args):
        self._refline("y", args)

    def f_annotation(self, *args):
        """
        ``annotation(type, x, y)`` for a ``line``, ``arrow``,
        ``doublearrow`` or ``textarrow``; ``annotation(type, dim)`` for a
        ``textbox``, ``rectangle`` or ``ellipse``. Positions are fractions of
        the figure, from its lower-left corner.
        """
        if not args or not isinstance(args[0], str):
            raise MatlabError("annotation needs the kind of shape first.")
        kind = args[0].lower()
        figs = self.rt.figures
        owner = figs.figure() or figs.ensure()
        figs.touch()
        entry: dict = {"type": kind}
        if kind in ("line", "arrow", "doublearrow", "textarrow"):
            if len(args) < 3:
                raise MatlabError(f"annotation('{kind}', x, y) needs the "
                                  f"start and end as x = [x1 x2], y = [y1 y2].")
            entry["x"], entry["y"] = list(_vector(args[1])), \
                list(_vector(args[2]))
            rest = args[3:]
        elif kind in ("textbox", "rectangle", "ellipse"):
            if len(args) >= 2 and not isinstance(args[1], str):
                entry["position"] = list(_vector(args[1]))
                rest = args[2:]
            else:
                rest = args[1:]
        else:
            raise MatlabError(f"annotation: unknown kind '{args[0]}'.")
        _data, props, _flags = _options(rest)
        if "position" in props:
            entry["position"] = list(props.pop("position").reshape(-1))
        if kind in ("textbox", "rectangle", "ellipse") and \
                len(entry.get("position", ())) != 4:
            raise MatlabError(f"annotation('{kind}', [x y w h]): the "
                              f"position is four numbers.")
        entry.update(props)
        if kind == "textbox" and "edgecolor" not in entry:
            entry["edgecolor"] = "#000000"
        owner.extra.setdefault("annotations", []).append(entry)

    # ── saving figures ──────────────────────────────────────────

    def _figure_for(self, handle) -> FigureSpec:
        figs = self.rt.figures
        spec = None
        if isinstance(handle, Graphic):
            spec = handle.figure
        elif _is_number(handle) and 1 <= int(handle) <= len(figs.specs):
            spec = figs.specs[int(handle) - 1]
        spec = spec or figs.figure()
        if spec is None or spec not in figs.drawable():
            raise MatlabError("There is no figure to save.")
        return spec

    def f_saveas(self, fig, filename, fmt=None):
        path = self.rt.resolve(filename)
        if not os.path.splitext(path)[1]:
            ext = str(fmt or "png").lower().lstrip(".")
            path += "." + ("png" if ext == "fig" else ext)
        _mr._export_figure(self._figure_for(fig), path)

    def f_exportgraphics(self, obj, filename, *args):
        """``exportgraphics(gcf, file)``, with ``'Resolution'`` in dots per inch."""
        options = {str(args[k]).lower(): args[k + 1]
                   for k in range(0, len(args) - 1, 2)}
        dpi = options.get("resolution")
        path = self.rt.resolve(filename)
        if not os.path.splitext(path)[1]:
            raise MatlabError("exportgraphics needs a file name with an "
                              "extension (.png, .pdf, .eps, .svg, .jpg, "
                              ".tif).")
        _mr._export_figure(self._figure_for(obj), path,
                           dpi=float(_scalar_of(dpi)) if dpi is not None
                           else None)

    def f_print(self, *args):
        fmt, filename, handle, dpi = "png", None, None, None
        for a in args:
            if isinstance(a, str) and a.startswith("-d"):
                fmt = a[2:].lower()
            elif isinstance(a, str) and re.fullmatch(r"-r\d+", a):
                dpi = float(a[2:]) or None
            elif isinstance(a, str) and a.startswith("-"):
                continue                       # -painters, -vector, …
            elif isinstance(a, str):
                filename = a
            else:
                handle = a
        if filename is None:
            raise MatlabError("Printing to a printer is not supported; give "
                              "print a file name.")
        path = self.rt.resolve(filename)
        if not os.path.splitext(path)[1]:
            path += {"jpeg": ".jpg", "tiff": ".tif", "tiffn": ".tif",
                     "epsc": ".eps", "eps2": ".eps", "epsc2": ".eps",
                     "meta": ".emf"}.get(fmt, "." + fmt)
        _mr._export_figure(self._figure_for(handle), path, dpi=dpi)


def _make_colormap_function(name: str):
    @_nargout
    def f(self, n=256, nargout=1):
        return _colormap(name, int(_scalar_of(n)))
    f.__name__ = f"f_{name}"
    f.__doc__ = f"``{name}(n)``: the {name} colour map, n×3."
    return f


for _name in COLORMAPS:
    setattr(PlotLibrary, f"f_{_name}", _make_colormap_function(_name))
