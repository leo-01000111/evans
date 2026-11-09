"""
The real dialogs behind ``uigetfile``, ``inputdlg``, ``waitbar`` and the rest.

:mod:`evans.console.dialogs` decides what to ask; this host asks it with Qt.
User code runs on the GUI thread, so each call can simply open a modal dialog
(or a nested event loop) and return the answer. Tests replace the static Qt
entry points (``QFileDialog.getOpenFileNames``, ``QMessageBox.exec``, ...), so
nothing needs a person.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QLabel,
    QListWidget,
    QMessageBox,
    QPlainTextEdit,
    QProgressDialog,
    QVBoxLayout,
    QWidget,
)

from ...console.dialogs import Dialogs


def _filter_text(filters: list[tuple[str, str]]) -> str:
    """Qt's ``"Label (*.a *.b);;Label2 (*.*)"`` form of the filter list."""
    parts = []
    for patterns, label in filters:
        glob = " ".join(p.strip() for p in patterns.split(";") if p.strip())
        shown = label if "(" in label else f"{label} ({glob})"
        # Qt takes the part in the last brackets as the pattern list.
        if "(" in label:
            shown = f"{label.rsplit('(', 1)[0].strip()} ({glob})"
        parts.append(shown)
    return ";;".join(parts)


class _Form(QDialog):
    """``inputdlg``: a labelled text box per prompt."""

    def __init__(self, prompts, title, lines, defaults, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title or "Input")
        outer = QVBoxLayout(self)
        form = QFormLayout()
        outer.addLayout(form)
        self.fields: list[QPlainTextEdit] = []
        for prompt, rows, default in zip(prompts, lines, defaults):
            box = QPlainTextEdit(default)
            box.setTabChangesFocus(True)
            line = box.fontMetrics().lineSpacing()
            box.setFixedHeight(line * max(rows, 1) + 12)
            if rows <= 1:
                box.setLineWrapMode(QPlainTextEdit.NoWrap)
                box.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            form.addRow(QLabel(prompt), box)
            self.fields.append(box)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok
                                   | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)
        self.setMinimumWidth(360)

    def values(self) -> list[str]:
        return [f.toPlainText() for f in self.fields]


class _Choice(QDialog):
    """``listdlg``."""

    def __init__(self, items, title, prompt, multiple, initial,
                 parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title or "Select")
        outer = QVBoxLayout(self)
        if prompt:
            outer.addWidget(QLabel(prompt))
        self.list = QListWidget()
        self.list.addItems(items)
        self.list.setSelectionMode(
            QListWidget.ExtendedSelection if multiple
            else QListWidget.SingleSelection)
        for i in initial:
            if 0 <= i < self.list.count():
                self.list.item(i).setSelected(True)
        self.list.itemDoubleClicked.connect(lambda _item: self.accept())
        outer.addWidget(self.list)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok
                                   | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

    def picked(self) -> list[int]:
        return sorted(self.list.row(i) for i in self.list.selectedItems())


class QtDialogs(Dialogs, QObject):
    """Opens real dialogs over ``parent`` (the window), on the GUI thread."""

    def __init__(self, parent: QWidget | None = None, *, console=None,
                 figures=None) -> None:
        QObject.__init__(self)
        self._parent = parent
        #: The console widget, for ``input``; the figure area, for ``ginput``.
        self.console = console
        self.figures = figures
        self._bars: dict[int, QProgressDialog] = {}
        self._next = 0

    def _owner(self) -> QWidget | None:
        return self._parent or QApplication.activeWindow()

    def open_files(self, title, filters, start, multiple):
        text = _filter_text(filters)
        if multiple:
            paths, _ = QFileDialog.getOpenFileNames(
                self._owner(), title, start, text)
            return list(paths) or None
        path, _ = QFileDialog.getOpenFileName(
            self._owner(), title, start, text)
        return [path] if path else None

    def save_file(self, title, filters, default):
        path, _ = QFileDialog.getSaveFileName(
            self._owner(), title, default, _filter_text(filters))
        return path or None

    def directory(self, title, start):
        path = QFileDialog.getExistingDirectory(self._owner(), title, start)
        return path or None

    def form(self, prompts, title, lines, defaults):
        dialog = _Form(prompts, title, lines, defaults, self._owner())
        return dialog.values() if dialog.exec() == QDialog.Accepted else None

    def message(self, kind, text, title):
        icon = {"error": QMessageBox.Critical, "warn": QMessageBox.Warning,
                "help": QMessageBox.Question}.get(kind,
                                                  QMessageBox.Information)
        box = QMessageBox(icon, title or {
            "error": "Error", "warn": "Warning"}.get(kind, "Message"),
            text, QMessageBox.Ok, self._owner())
        box.exec()

    def question(self, text, title, buttons, default):
        box = QMessageBox(QMessageBox.Question, title, text,
                          QMessageBox.NoButton, self._owner())
        made = {}
        for name in buttons:
            made[box.addButton(name, QMessageBox.ActionRole)] = name
            if name == default:
                box.setDefaultButton(box.buttons()[-1])
        box.exec()
        return made.get(box.clickedButton())

    def choose(self, items, title, prompt, multiple, initial):
        dialog = _Choice(items, title, prompt, multiple, initial,
                         self._owner())
        return dialog.picked() if dialog.exec() == QDialog.Accepted else None

    def waitbar(self, ident, fraction, text, title):
        bar = self._bars.get(ident) if ident else None
        if bar is None:
            self._next += 1
            ident = self._next
            bar = QProgressDialog(text, None, 0, 100, self._owner())
            bar.setWindowTitle(title or "Waitbar")
            bar.setWindowModality(Qt.NonModal)
            bar.setAutoClose(False)
            bar.setAutoReset(False)
            bar.setMinimumDuration(0)
            self._bars[ident] = bar
            bar.show()
        if text:
            bar.setLabelText(text)
        bar.setValue(int(round(fraction * 100)))
        QApplication.processEvents()
        return ident

    def close_waitbar(self, ident):
        bar = self._bars.pop(ident, None)
        if bar is None:
            return False
        bar.close()
        bar.deleteLater()
        return True

    def points(self, count):
        view = self.figures.current_figure() if self.figures else None
        if view is None:
            return []
        return view.collect_points(count)

    def read_line(self, prompt):
        if self.console is None:
            return None
        return self.console.read_line(prompt)
