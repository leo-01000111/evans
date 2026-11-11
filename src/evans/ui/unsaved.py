"""
Unsaved work: the mark a title or file name carries, and the question asked
before it is closed, quit or replaced.

The script tabs, the live script and the Model tab all ask the same way:
Save, Discard or Cancel.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

#: After a tab title or file name whose content is not saved.
UNSAVED_MARK = " ●"


def marked(name: str, unsaved: bool) -> str:
    """``name``, with the unsaved mark when ``unsaved``."""
    return name + (UNSAVED_MARK if unsaved else "")


def ask_to_save(parent: QWidget | None, title: str, text: str) -> str:
    """Save, Discard or Cancel: returns 'save', 'discard' or 'cancel'."""
    box = QMessageBox(
        QMessageBox.Question, title, text,
        QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, parent)
    box.setDefaultButton(QMessageBox.Save)
    answer = box.exec()
    return {QMessageBox.Save: "save",
            QMessageBox.Discard: "discard"}.get(answer, "cancel")
