"""
The Model scripts dialog: the ``.m`` files a model runs, and when.
=================================================================
An ordered list, each row ticked for *On open*, *Before run*, or both (see
:mod:`evans.sim.scripts`). Rows move up and down, since the order is the run
order; *Run now* runs the selected rows (all of them if none is selected) in
the console straight away. A file that is not where the row says is shown as
missing, and stays listed until it is removed.

Nothing changes on the model until OK.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QItemSelectionModel, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ...sim.model import SimModel
from ...sim.scripts import ModelScript, resolve, stored_path
from ..design import NORMAL

#: The table's columns.
NAME, ON_OPEN, BEFORE_RUN = range(3)


class ModelScriptsDialog(QDialog):
    """Edit a copy of ``model.scripts``; :meth:`scripts` is the result."""

    def __init__(self, model: SimModel, parent=None, *,
                 run_now: Callable[[list[ModelScript]], object] | None = None,
                 search: Callable[[], list] = list) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Model scripts — {model.name}")
        self._model_path = model.path
        self._search = search
        self._run_now = run_now
        self._scripts = [ModelScript(s.path, s.on_open, s.before_run)
                         for s in model.scripts]

        intro = QLabel(
            "MATLAB scripts this model runs in the console's workspace, top "
            "to bottom: when it opens, before every run, or both. Use them to "
            "set the variables its blocks name (Kp, Ts, a plant's matrices). "
            "Paths are kept relative to the model file where they can be.")
        intro.setWordWrap(True)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(
            ["Script", "On open", "Before run"])
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(NAME, QHeaderView.Stretch)
        header.setSectionResizeMode(ON_OPEN, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(BEFORE_RUN, QHeaderView.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self._table.itemChanged.connect(self._on_item_changed)

        self.add_button = QPushButton("Add…")
        self.add_button.clicked.connect(self._ask_files)
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self.remove_selected)
        self.up_button = QPushButton("Move up")
        self.up_button.clicked.connect(lambda: self.move_selected(-1))
        self.down_button = QPushButton("Move down")
        self.down_button.clicked.connect(lambda: self.move_selected(1))
        self.run_button = QPushButton("Run now")
        self.run_button.setToolTip(
            "Run the selected scripts (all of them if none is selected) in "
            "the console now")
        self.run_button.clicked.connect(self.run_now)
        self.run_button.setEnabled(run_now is not None)

        side = QVBoxLayout()
        for button in (self.add_button, self.remove_button, self.up_button,
                       self.down_button):
            side.addWidget(button)
        side.addStretch(1)
        side.addWidget(self.run_button)

        row = QHBoxLayout()
        row.setSpacing(NORMAL)
        row.addWidget(self._table, stretch=1)
        row.addLayout(side)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok
                                   | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addLayout(row, stretch=1)
        layout.addWidget(buttons)
        self.resize(620, 340)
        self._fill()

    # ── the list ────────────────────────────────────────────────

    def scripts(self) -> list[ModelScript]:
        """The list as it stands, in order."""
        return [ModelScript(s.path, s.on_open, s.before_run)
                for s in self._scripts]

    def add_files(self, paths) -> None:
        """Add ``.m`` files at the end, ticked for both; one already listed
        is not added twice."""
        known = {s.path for s in self._scripts}
        for path in paths:
            text = stored_path(path, self._model_path)
            if text not in known:
                self._scripts.append(ModelScript(text, True, True))
                known.add(text)
        self._fill(select=[len(self._scripts) - 1] if self._scripts else [])

    def remove_selected(self) -> None:
        rows = set(self._selected_rows())
        self._scripts = [s for i, s in enumerate(self._scripts)
                         if i not in rows]
        self._fill()

    def move_selected(self, step: int) -> None:
        """Move the selected rows up (``-1``) or down (``1``) one place."""
        rows = self._selected_rows()
        if not rows:
            return
        if (step < 0 and rows[0] == 0) or \
                (step > 0 and rows[-1] == len(self._scripts) - 1):
            return
        order = list(range(len(self._scripts)))
        for row in (rows if step < 0 else reversed(rows)):
            order[row], order[row + step] = order[row + step], order[row]
        self._scripts = [self._scripts[i] for i in order]
        self._fill(select=[r + step for r in rows])

    def run_now(self) -> None:
        if self._run_now is None:
            return
        rows = self._selected_rows()
        chosen = [self._scripts[r] for r in rows] if rows else self._scripts
        if chosen:
            self._run_now([ModelScript(s.path, s.on_open, s.before_run)
                           for s in chosen])
            self._fill(select=rows)

    # ── the table ───────────────────────────────────────────────

    def _ask_files(self) -> None:
        folder = str(Path(self._model_path).parent) \
            if self._model_path is not None else ""
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Add model scripts", folder,
            "MATLAB scripts (*.m);;All files (*)")
        if paths:
            self.add_files(paths)

    def _selected_rows(self) -> list[int]:
        return sorted({index.row() for index in
                       self._table.selectionModel().selectedRows()})

    def _fill(self, select: list[int] | None = None) -> None:
        table = self._table
        table.blockSignals(True)
        try:
            table.setRowCount(len(self._scripts))
            search = self._search()
            for row, script in enumerate(self._scripts):
                found = resolve(script, self._model_path, search)
                name = QTableWidgetItem(
                    script.path if found else f"{script.path}  (not found)")
                name.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                name.setToolTip(str(found) if found else
                                "This file is not there: it will be skipped "
                                "on open, and stop a run it is ticked for.")
                if not found:
                    font = name.font()
                    font.setItalic(True)
                    name.setFont(font)
                table.setItem(row, NAME, name)
                for column, on in ((ON_OPEN, script.on_open),
                                   (BEFORE_RUN, script.before_run)):
                    item = QTableWidgetItem()
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable
                                  | Qt.ItemIsUserCheckable)
                    item.setCheckState(Qt.Checked if on else Qt.Unchecked)
                    table.setItem(row, column, item)
        finally:
            table.blockSignals(False)
        table.clearSelection()
        chosen = table.selectionModel()
        for row in select or []:
            if 0 <= row < table.rowCount():
                chosen.select(table.model().index(row, 0),
                              QItemSelectionModel.Select
                              | QItemSelectionModel.Rows)
        has = bool(self._scripts)
        for button in (self.remove_button, self.up_button, self.down_button):
            button.setEnabled(has)

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if item.column() == NAME or item.row() >= len(self._scripts):
            return
        on = item.checkState() == Qt.Checked
        script = self._scripts[item.row()]
        if item.column() == ON_OPEN:
            script.on_open = on
        else:
            script.before_run = on
