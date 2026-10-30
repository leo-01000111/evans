"""
Block parameter editing, built from the block's own ``params_spec``.

Nothing here knows about any particular block: the widget for each parameter
follows from its declared ``kind``, so a new block gets a working editor with
no UI changes. Values are validated by handing them to a throwaway copy of the
block before the dialog closes — if the block would reject them, the dialog
says so instead of letting a broken model reach the canvas.

A numeric parameter is a text box, not a spin box, because it takes a MATLAB
expression as readily as a number: ``Kp``, ``2*pi*f``, ``[1 2 3]``. The
expression is evaluated in the console workspace when the model runs (see
:mod:`evans.sim.workspace`), so it is not checked here beyond its syntax.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from ...sim.block import Block, BlockError, create, is_expression
from .. import theme


class ParamForm(QWidget):
    """
    The editors for one block's parameters, without any container.

    Shared by the modal dialog and the docked inspector so there is one
    implementation of "what widget does a `matrix` parameter get?" — the
    reason a new block type still needs no UI changes.
    """

    def __init__(self, block: Block, parent=None) -> None:
        super().__init__(parent)
        self.block = block

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        header = QLabel(block.description)
        header.setWordWrap(True)
        header.setStyleSheet("color: palette(mid);")
        root.addWidget(header)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        self._editors: dict[str, Any] = {}
        raw = block.raw_params()
        for spec in block.params_spec:
            if spec.kind == "model":
                continue                    # a subsystem's contents
            widget = self._make_editor(spec, raw[spec.name])
            if spec.help:
                widget.setToolTip(spec.help)
            widget.setAccessibleName(spec.label)
            self._editors[spec.name] = widget
            form.addRow(spec.label + ":", widget)
        root.addLayout(form)

        self._error = QLabel("")
        self._error.setWordWrap(True)
        self._error.hide()
        root.addWidget(self._error)
        self._restyle()
        theme.notifier().changed.connect(self._restyle)

    def _restyle(self, *_args) -> None:
        self._error.setStyleSheet(f"color: {theme.tokens().hold_ink};")

    # ── editors ─────────────────────────────────────────────────

    @staticmethod
    def _make_editor(spec, value):
        if spec.kind == "bool":
            w = QCheckBox()
            w.setChecked(bool(value))
            return w
        if spec.kind == "int":
            w = QSpinBox()
            w.setRange(-10_000_000, 10_000_000)
            w.setValue(int(value))
            return w
        if spec.kind == "choice":
            w = QComboBox()
            w.addItems([str(c) for c in spec.choices])
            idx = w.findText(str(value))
            w.setCurrentIndex(max(idx, 0))
            return w
        if spec.kind == "code":
            w = QPlainTextEdit(str(value))
            w.setFont(theme.data_font(9))
            lines = str(value).count("\n") + 1
            w.setMinimumHeight(40 if lines == 1 else 140)
            w.setPlaceholderText("MATLAB code")
            return w
        if spec.kind == "matrix":
            w = QPlainTextEdit(_text(value))
            w.setMaximumHeight(72)
            w.setPlaceholderText("0 1; -2 -3, or a variable such as A")
            return w
        w = QLineEdit(_text(value))
        if spec.kind in ("float", "vector", "data"):
            w.setPlaceholderText("a number, or an expression such as Kp")
        return w

    def _value(self, name: str) -> Any:
        widget = self._editors[name]
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        if isinstance(widget, QSpinBox):
            return widget.value()
        if isinstance(widget, QComboBox):
            return widget.currentText()
        if isinstance(widget, QPlainTextEdit):
            return widget.toPlainText()
        return widget.text()

    # ── validation ──────────────────────────────────────────────

    def commit(self) -> dict[str, Any] | None:
        """
        The changed parameters, or ``None`` if they would be rejected.

        Validated on a throwaway instance: the live block keeps its old
        parameters until the undo command applies the new ones, so a rejected
        edit cannot leave a half-configured block behind.
        """
        values = {name: self._value(name) for name in self._editors}
        for spec in self.block.params_spec:
            text = values.get(spec.name)
            if spec.kind == "float" and isinstance(text, str):
                if not text.strip():
                    self._fail(f"{spec.label} is empty")
                    return None
                if not is_expression("float", text):
                    values[spec.name] = float(text)
        try:
            create(self.block.type_name, "__validate__", **values)
        except (BlockError, ValueError) as exc:
            self._fail(str(exc))
            return None

        self._error.hide()
        raw = self.block.raw_params()
        return {k: v for k, v in values.items() if not _same(v, raw[k])}

    def _fail(self, message: str) -> None:
        self._error.setText(message)
        self._error.show()


def _text(value) -> str:
    """A parameter as its editor shows it."""
    if isinstance(value, float):
        return f"{value:.12g}"
    if isinstance(value, np.ndarray):
        if value.ndim == 2:
            return "; ".join(" ".join(f"{v:.12g}" for v in row)
                             for row in value)
        return ", ".join(f"{v:.12g}" for v in value)
    if isinstance(value, (list, tuple)):
        return ", ".join(_text(v) for v in value)
    return str(value)


def _same(a, b) -> bool:
    """Whether an edited value is the one already there."""
    if isinstance(a, str) or isinstance(b, str):
        return a == b
    try:
        return bool(np.array_equal(np.asarray(a), np.asarray(b)))
    except (TypeError, ValueError):
        return a == b


class ParamDialog(QDialog):
    """Edit one block's parameters, modally."""

    def __init__(self, block: Block, parent=None) -> None:
        super().__init__(parent)
        self.block = block
        self.changes: dict[str, Any] = {}
        self.setWindowTitle(f"{block.type_name} — {block.block_id}")
        self.setMinimumWidth(380)

        root = QVBoxLayout(self)
        self.form = ParamForm(block)
        root.addWidget(self.form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _accept(self) -> None:
        changes = self.form.commit()
        if changes is None:
            self.adjustSize()
            return
        self.changes = changes
        self.accept()
