"""
Where a plot command's output goes.

``step(G)`` in a console has to draw somewhere. Rather than let the API import
Qt — which would make the whole namespace untestable headless and drag a GUI
into every script — a plot command builds a :class:`FigureSpec` describing
what to draw and hands it to the installed **sink**.

The UI installs a sink that opens a docked figure window. The default sink
just remembers the last few specs, so the API can be tested, scripted and run
headless with no display at all.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class Trace:
    """
    One curve on a figure — or one surface, image, patch or field of arrows.

    ``style`` names what it is. The 2-D styles are ``line``, ``dashed``,
    ``scatter``, ``stem``, ``bar``, ``errorbar``, ``area``, ``fill`` (a
    polygon), ``image``, ``contour``, ``contourf`` and ``quiver``; the 3-D
    ones, which have a ``z``, are ``line3``, ``scatter3``, ``surface``,
    ``mesh`` and ``quiver3``. A surface, image or contour keeps its grid
    as given: ``x`` and ``y`` the axes' vectors or matrices, ``z`` the
    matrix.

    ``props`` holds what the script asked for beyond the data, in renderer-
    neutral terms: ``color`` and ``edgecolor`` (hex), ``marker`` (MATLAB's
    letter), ``linewidth``, ``markersize``, ``alpha``, ``side`` (``"right"``
    for ``yyaxis right``), and each style's own (``yneg``/``ypos`` for error
    bars, ``u``/``v`` for arrows, ``levels`` for contours, …).
    """
    x:     np.ndarray
    y:     np.ndarray
    label: str = ""
    style: str = "line"
    z:     np.ndarray | None = None
    props: dict[str, Any] = field(default_factory=dict)


@dataclass
class FigureSpec:
    """
    A plot request, described rather than drawn.

    ``kind`` tells the sink which axes to build — ``"time"``, ``"bode"``,
    ``"nyquist"``, ``"pzmap"``, ``"rlocus"``, ``"xy"``, ``"pie"`` or
    ``"subplot"`` (a grid of other specs) — so the renderer can apply the
    right scales and annotations without the API knowing anything about
    widgets. An ``"xy"`` figure with a 3-D trace is drawn on 3-D axes.

    Axes-wide settings live in ``extra``: ``xlim``/``ylim``/``zlim``,
    ``logx``/``logy``, ``grid``, ``zlabel``, ``texts`` (``text`` calls),
    ``xlines``/``ylines``, ``colormap`` (an n×3 array), ``colorbar``,
    ``clim``, ``view`` (azimuth, elevation), ``colororder``, ``aspect``
    (``"equal"``), ``ydir`` (``"reverse"``), ``axis_off``, ``right`` (the
    ``yyaxis right`` labels and limits) and ``annotations`` (``annotation``
    shapes in figure-normalised units).
    """
    kind:    str
    title:   str = ""
    xlabel:  str = ""
    ylabel:  str = ""
    traces:  list[Trace] = field(default_factory=list)
    extra:   dict[str, Any] = field(default_factory=dict)

    def add(self, x, y, label: str = "", style: str = "line", z=None,
            **props) -> FigureSpec:
        self.traces.append(Trace(
            np.asarray(x, dtype=float), np.asarray(y, dtype=float), label,
            style, None if z is None else np.asarray(z, dtype=float),
            dict(props)))
        return self

    @property
    def is_3d(self) -> bool:
        """Whether this figure needs 3-D axes."""
        return any(t.style in STYLES_3D for t in self.traces)


#: The trace styles drawn on 3-D axes.
STYLES_3D = frozenset({"line3", "scatter3", "surface", "mesh", "quiver3",
                       "fill3", "contour3"})


class _RecordingSink:
    """Default sink: remember what was asked for, draw nothing."""

    def __init__(self, limit: int = 32) -> None:
        self.figures: list[FigureSpec] = []
        self._limit = limit

    def __call__(self, spec: FigureSpec) -> FigureSpec:
        self.figures.append(spec)
        del self.figures[:-self._limit]
        return spec

    @property
    def last(self) -> FigureSpec | None:
        return self.figures[-1] if self.figures else None

    def clear(self) -> None:
        self.figures.clear()


_sink: Callable[[FigureSpec], Any] = _RecordingSink()


def set_figure_sink(sink: Callable[[FigureSpec], Any]) -> Callable:
    """Install the renderer. Returns the previous one, so it can be restored."""
    global _sink
    previous, _sink = _sink, sink
    return previous


def figure_sink() -> Callable[[FigureSpec], Any]:
    """The sink currently installed."""
    return _sink


def emit(spec: FigureSpec) -> FigureSpec:
    """Send a figure to the installed sink."""
    _sink(spec)
    return spec


def recording_sink() -> _RecordingSink:
    """A fresh recording sink, for tests and headless scripts."""
    return _RecordingSink()
