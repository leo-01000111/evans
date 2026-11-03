"""
Pictures with nothing to install: math and figures through matplotlib.

Why matplotlib
--------------
Math in text cells has to be drawn in the app. The two candidates were
**matplotlib's mathtext** and **QtWebEngine with a vendored KaTeX**.
matplotlib is already a hard runtime dependency — python-control imports it
at module level, so it is in every install and in the frozen build (see
``packaging/evans.spec``). WebEngine is in the dev environment but is
deliberately *excluded* from the frozen build, where it would be the largest
thing in it. mathtext covers the TeX a lab report uses — fractions, sums,
integrals, roots, Greek, accents, sub/superscripts — and renders to a PNG
that a QTextDocument, an HTML page and a LaTeX report can all use. What it
cannot parse (``\\begin{bmatrix}``, say) falls back to showing the source.

The same module draws a :class:`FigureSpec` to a PNG for the reports, so a
report can be written headless — no widget has to be on screen to be grabbed.
"""

from __future__ import annotations

import io
from functools import lru_cache

from ..figures import FigureSpec


class MathError(ValueError):
    """mathtext could not parse the LaTeX."""


@lru_cache(maxsize=512)
def math_png(latex: str, *, display: bool = False, color: str = "#121314",
             fontsize: float = 11.0, dpi: int = 120) -> bytes:
    """
    Render LaTeX math to a transparent, tightly cropped PNG.

    Raises :class:`MathError` when mathtext cannot parse it. Display math is
    drawn a size larger, as TeX's display style is.
    """
    from matplotlib.figure import Figure
    from matplotlib.font_manager import FontProperties

    text = " ".join(latex.split())
    if not text:
        raise MathError("empty equation")
    size = fontsize * (1.2 if display else 1.0)
    figure = Figure(figsize=(0.01, 0.01))
    figure.text(0, 0, f"${text}$", fontproperties=FontProperties(size=size),
                color=color)
    buffer = io.BytesIO()
    try:
        figure.savefig(buffer, dpi=dpi, format="png", transparent=True,
                       bbox_inches="tight", pad_inches=0.02)
    except ValueError as exc:
        lines = [line.strip() for line in str(exc).splitlines()]
        raise MathError(next((line for line in lines if line),
                             "unparseable")) from exc
    return buffer.getvalue()


def png_size(data: bytes) -> tuple[int, int]:
    """Width and height of a PNG, read from its header."""
    return (int.from_bytes(data[16:20], "big"),
            int.from_bytes(data[20:24], "big"))


# ──────────────────────────────────────────────────────────────
#  Figures
# ──────────────────────────────────────────────────────────────

def figure_png(spec: FigureSpec, path=None, *, width: float = 6.4,
               height: float = 3.6, dpi: int = 150) -> bytes:
    """
    Draw a figure spec with matplotlib's Agg canvas; returns the PNG bytes
    and writes them to ``path`` too if one is given.

    Every kind the console produces is drawn, by :mod:`..figure_mpl` — the
    same renderer that writes a figure as PDF or EPS; the live figure in the
    app stays the reference rendering.
    """
    from ..figure_mpl import png

    data = png(spec, width=width, height=height, dpi=dpi)
    if path is not None:
        with open(path, "wb") as handle:
            handle.write(data)
    return data
