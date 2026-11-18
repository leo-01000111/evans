"""
A Scope block's own view: double-click the block and its signals open here.

Each scope plots only what is wired into its block, with the same
:class:`~evans.ui.sim.scope.ScopeWidget` the global scope uses, so copy,
Export… and "Compare with earlier runs" work the same. The Model tab keeps one
per block (keyed by the block's path, ``"Sub/Scope1"`` inside a subsystem),
redraws them when a run finishes, and closes them when a different model is
put on the canvas.

The plot lives in a :class:`ScopeView`, which is either the content of a
:class:`ScopeWindow` or a tab of the Model side panel. Docking and undocking
move that one widget, so its curves, ticked channels and compare setting
survive.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from ..design import TIGHT
from .scope import ScopeWidget

#: What the window says instead of an empty plot.
NOT_RUN = "Run the model to see this scope."
NOT_IN_RUN = ("This Scope block was not in the last run. Run the model again "
              "to see it.")
NOTHING_WIRED = "Nothing is wired into this Scope block."


class ScopeView(QWidget):
    """One Scope block's plot and its Dock / Undock button."""

    #: The Dock (or Undock) button was pressed; carries the key.
    dock_toggled = Signal(str)
    #: The title or model name changed (a run, a new model name).
    retitled = Signal()

    def __init__(self, key: str, title: str, model_name: str,
                 parent=None) -> None:
        super().__init__(parent)
        #: The block's path in the model, as the run result keys it.
        self.key = key
        self._title = title
        self._model_name = model_name
        self._docked = False

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        bar = QHBoxLayout()
        bar.setContentsMargins(TIGHT, TIGHT, TIGHT, 0)
        bar.addStretch()
        self._dock = QToolButton()
        self._dock.setAutoRaise(True)
        self._dock.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self._dock.clicked.connect(lambda: self.dock_toggled.emit(self.key))
        bar.addWidget(self._dock)
        root.addLayout(bar)
        self._stack = QStackedWidget()
        self._message = QLabel(NOT_RUN)
        self._message.setAlignment(Qt.AlignCenter)
        self._message.setWordWrap(True)
        self._message.setStyleSheet("color: palette(mid);")
        self.scope = ScopeWidget(title=title, signals=[])
        self._stack.addWidget(self._message)
        self._stack.addWidget(self.scope)
        root.addWidget(self._stack, stretch=1)
        self.set_docked(False)

    @property
    def title(self) -> str:
        return self._title

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def docked(self) -> bool:
        return self._docked

    @property
    def dock_button(self) -> QToolButton:
        return self._dock

    def set_docked(self, docked: bool) -> None:
        """Dressed for the side panel (the button says Undock) or a window."""
        self._docked = bool(docked)
        if self._docked:
            self._dock.setText("Undock")
            self._dock.setToolTip("Move this scope into a window of its own")
            self._dock.setAccessibleName("Undock scope")
        else:
            self._dock.setText("Dock")
            self._dock.setToolTip("Move this scope into the Model side panel")
            self._dock.setAccessibleName("Dock scope")

    def message(self) -> str:
        """What the view says, or "" when it shows the plot."""
        if self._stack.currentWidget() is self._message:
            return self._message.text()
        return ""

    def show_result(self, result, model_name: str | None = None,
                    history: list | None = None) -> None:
        """
        Draw this block's signals from ``result`` (None: not run yet).

        ``history`` seeds "Compare with earlier runs" for a view opened
        after several runs; once open, the view keeps its own.
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
        self.retitled.emit()
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

    def _say(self, text: str) -> None:
        self._message.setText(text)
        self._stack.setCurrentWidget(self._message)
        self.retitled.emit()


class ScopeWindow(QWidget):
    """A :class:`ScopeView` in a window of its own."""

    #: The window was closed; carries its key.
    closed = Signal(str)

    def __init__(self, key: str, title: str, model_name: str,
                 parent=None, view: ScopeView | None = None) -> None:
        super().__init__(parent, Qt.Window)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.key = key
        self._released = False
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.view = view or ScopeView(key, title, model_name)
        self._layout.addWidget(self.view)
        self.view.set_docked(False)
        self.view.retitled.connect(self._update_title)
        self._update_title()
        self.resize(720, 440)

    @property
    def scope(self) -> ScopeWidget:
        return self.view.scope

    def message(self) -> str:
        return self.view.message()

    def show_result(self, result, model_name: str | None = None,
                    history: list | None = None) -> None:
        self.view.show_result(result, model_name, history)

    def release_view(self) -> ScopeView:
        """
        Hand the view over (to be docked) and close without announcing it:
        the scope is not gone, only moved.
        """
        self._released = True
        self.view.retitled.disconnect(self._update_title)
        self._layout.removeWidget(self.view)
        self.view.setParent(None)
        self.close()
        return self.view

    def closeEvent(self, event) -> None:            # noqa: N802 (Qt API)
        if not self._released:
            self.closed.emit(self.key)
        super().closeEvent(event)

    def _update_title(self) -> None:
        self.setWindowTitle(f"{self.view.title} — {self.view.model_name}")
