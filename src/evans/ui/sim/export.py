"""
The block diagram, out of the app: SVG, PDF, PNG or JPEG, and the printer.

The scene is drawn as the canvas shows it, in the current theme's colours on
its ground, with the selection cleared first so a selected block does not
come out highlighted. SVG and PDF are vector, so a diagram dropped into a
report stays sharp at any size.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QMarginsF, QRectF, QSize, QSizeF
from PySide6.QtGui import QColor, QImage, QPageLayout, QPageSize, QPainter

from .. import theme

#: Space round the drawing, in scene units.
MARGIN = 24.0
#: Pixels per scene unit in a PNG or JPEG, so it is crisp on a modern screen.
RASTER_SCALE = 2.0


def export_scene(scene, path) -> Path:
    """Draw ``scene`` into ``path``; the extension picks the format."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix not in (".svg", ".pdf", ".png", ".jpg", ".jpeg"):
        raise ValueError(f"cannot export a diagram as {suffix or 'that'}; "
                         f"use .svg, .pdf or .png")
    selected = scene.selectedItems()
    scene.clearSelection()
    try:
        source = scene.itemsBoundingRect().adjusted(-MARGIN, -MARGIN,
                                                    MARGIN, MARGIN)
        if source.isEmpty():
            source = QRectF(0, 0, 200, 100)
        if suffix == ".svg":
            _svg(scene, source, path)
        elif suffix == ".pdf":
            _pdf(scene, source, path)
        else:
            _raster(scene, source, path)
    finally:
        for item in selected:
            item.setSelected(True)
    return path


def _ground(painter: QPainter, rect: QRectF) -> None:
    painter.fillRect(rect, QColor(theme.tokens().ground))


def _svg(scene, source: QRectF, path: Path) -> None:
    from PySide6.QtSvg import QSvgGenerator
    generator = QSvgGenerator()
    generator.setFileName(str(path))
    generator.setSize(source.size().toSize())
    generator.setViewBox(QRectF(0, 0, source.width(), source.height()))
    generator.setTitle(path.stem)
    painter = QPainter(generator)
    target = QRectF(0, 0, source.width(), source.height())
    _ground(painter, target)
    scene.render(painter, target, source)
    painter.end()


def _pdf(scene, source: QRectF, path: Path) -> None:
    from PySide6.QtGui import QPdfWriter
    writer = QPdfWriter(str(path))
    writer.setTitle(path.stem)
    # A page the size of the drawing, in points: no scaling, no blank A4.
    writer.setPageSize(QPageSize(QSizeF(source.width(), source.height()),
                                 QPageSize.Point))
    writer.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Point)
    painter = QPainter(writer)
    target = QRectF(painter.viewport())
    _ground(painter, target)
    scene.render(painter, target, source)
    painter.end()


def _raster(scene, source: QRectF, path: Path) -> None:
    size = QSize(int(source.width() * RASTER_SCALE),
                 int(source.height() * RASTER_SCALE))
    image = QImage(size, QImage.Format_ARGB32)
    image.fill(QColor(theme.tokens().ground))
    painter = QPainter(image)
    painter.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing)
    scene.render(painter, QRectF(0, 0, size.width(), size.height()), source)
    painter.end()
    if not image.save(str(path)):
        raise OSError(f"could not write {path}")


def print_scene(scene, parent=None) -> bool:
    """Ask for a printer and print the diagram, fitted to the page."""
    from PySide6.QtPrintSupport import QPrintDialog, QPrinter
    printer = QPrinter(QPrinter.HighResolution)
    dialog = QPrintDialog(printer, parent)
    if dialog.exec() != QPrintDialog.Accepted:
        return False
    selected = scene.selectedItems()
    scene.clearSelection()
    try:
        source = scene.itemsBoundingRect().adjusted(-MARGIN, -MARGIN,
                                                    MARGIN, MARGIN)
        painter = QPainter(printer)
        scene.render(painter, QRectF(painter.viewport()), source)
        painter.end()
    finally:
        for item in selected:
            item.setSelected(True)
    return True
