"""
A Scope block's own window: double-click the block and its signals open here.

Each window plots only what is wired into its block, with the same
:class:`~evans.ui.sim.scope.ScopeWidget` the global scope uses, so copy,
Export… and "Compare with earlier runs" work the same. The Model tab keeps one
window per block (keyed by the block's path, ``"Sub/Scope1"`` inside a
subsystem), redraws the open ones when a run finishes, and closes them when a
different model is put on the canvas.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QStackedWidget, QVBoxLayout, QWidget

from .scope import ScopeWidget

#: What the window says instead of an empty plot.
NOT_RUN = "Run the model to see this scope."
NOT_IN_RUN = ("This Scope block was not in the last run. Run the model again "
              "to see it.")
NOTHING_WIRED = "Nothing is wired into this Scope block."


class ScopeWindow(QWidget):
    """One Scope block's plot, in a window of its own."""

    #: The window was closed; carries its key.
    closed = Signal(str)

    def __init__(self, key: str, title: str, model_name: str,
                 parent=None) -> None:
        super().__init__(parent, Qt.Window)
        self.setAttribute(Qt.WA_DeleteOnClose)
        #: The block's path in the model, as the run result keys it.
        self.key = key
        self._title = title
        self._model_name = model_name

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self._stack = QStackedWidget()
        self._message = QLabel(NOT_RUN)
        self._message.setAlignment(Qt.AlignCenter)
        self._message.setWordWrap(True)
        self._message.setStyleSheet("color: palette(mid);")
        self.scope = ScopeWidget(title=title, signals=[])
        self._stack.addWidget(self._message)
        self._stack.addWidget(self.scope)
        root.addWidget(self._stack)
        self._update_title()
        self.resize(720, 440)

    def message(self) -> str:
        """What the window says, or "" when it shows the plot."""
        if self._stack.currentWidget() is self._message:
            return self._message.text()
        return ""

    def show_result(self, result, model_name: str | None = None,
                    history: list | None = None) -> None:
        """
        Draw this block's signals from ``result`` (None: not run yet).

        ``history`` seeds "Compare with earlier runs" for a window opened
        after several runs; once open, the window keeps its own.
        """
        if model_name is not None:
            self._model_name = model_name
        if result is None:
            self._say(NOT_RUN)
            return
        if self.key not in result.scope_blocks:
            self._say(NOT_IN_RUN)
            return
        self._title = result.scope_titles.get(self.key, self._title)
        self._update_title()
        sources = [s for s in result.scope_blocks[self.key]
                   if s in result.signals]
        if history is not None and self.scope.result is None:
            self.scope.history = list(history)
        self.scope.set_signals(sources)
        self.scope.set_title(self._title)
        self.scope.show_result(result)
        if not sources:
            self._say(NOTHING_WIRED)
            return
        self._stack.setCurrentWidget(self.scope)

    def closeEvent(self, event) -> None:            # noqa: N802 (Qt API)
        self.closed.emit(self.key)
        super().closeEvent(event)

    def _say(self, text: str) -> None:
        self._message.setText(text)
        self._stack.setCurrentWidget(self._message)

    def _update_title(self) -> None:
        self.setWindowTitle(f"{self._title} — {self._model_name}")
