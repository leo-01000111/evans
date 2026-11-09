"""
The Qt dialog host, offscreen: every Qt entry point is replaced by a stub, so
nothing waits for a person. The commands themselves are in ``test_lib_ui.py``.
"""

from __future__ import annotations

import pytest

pytest.importorskip("PySide6", reason="Qt not available")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox

from evans.console import Interpreter
from evans.console.dialogs import set_dialog_host
from evans.console.tracer import Interrupted
from evans.ui.console import dialog_host as host_module
from evans.ui.console.console_widget import ConsoleWidget
from evans.ui.console.dialog_host import QtDialogs


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def host(app):
    return QtDialogs(None)


def test_open_files_single_and_multiple(host, monkeypatch):
    seen = {}

    def one(parent, title, start, flt):
        seen["one"] = (title, start, flt)
        return "C:/d/a.m", flt

    def many(parent, title, start, flt):
        return ["C:/d/a.m", "C:/d/b.m"], flt

    monkeypatch.setattr(QFileDialog, "getOpenFileName", one)
    monkeypatch.setattr(QFileDialog, "getOpenFileNames", many)
    filters = [("*.m;*.mlx", "Code"), ("*.*", "All Files (*.*)")]
    assert host.open_files("Pick", filters, "C:/d", False) == ["C:/d/a.m"]
    assert host.open_files("Pick", filters, "C:/d", True) == [
        "C:/d/a.m", "C:/d/b.m"]
    title, start, flt = seen["one"]
    assert title == "Pick" and start == "C:/d"
    assert flt == "Code (*.m *.mlx);;All Files (*.*)"


def test_cancel_in_the_file_dialogs_is_none(host, monkeypatch):
    monkeypatch.setattr(QFileDialog, "getOpenFileName",
                        lambda *a: ("", ""))
    monkeypatch.setattr(QFileDialog, "getOpenFileNames",
                        lambda *a: ([], ""))
    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *a: ("", ""))
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a: "")
    assert host.open_files("t", [("*.*", "x")], "", False) is None
    assert host.open_files("t", [("*.*", "x")], "", True) is None
    assert host.save_file("t", [("*.*", "x")], "") is None
    assert host.directory("t", "") is None


def test_save_and_directory(host, monkeypatch):
    monkeypatch.setattr(QFileDialog, "getSaveFileName",
                        lambda *a: ("C:/o/x.mat", ""))
    monkeypatch.setattr(QFileDialog, "getExistingDirectory",
                        lambda *a: "C:/o")
    assert host.save_file("t", [("*.mat", "MAT")], "C:/o/x.mat") == "C:/o/x.mat"
    assert host.directory("t", "C:/") == "C:/o"


def test_the_input_form_shows_defaults_and_returns_what_is_in_it(
        host, monkeypatch):
    def accept(self):
        self.fields[0].setPlainText("changed")
        return QDialog.Accepted

    monkeypatch.setattr(host_module._Form, "exec", accept)
    out = host.form(["A", "B"], "T", [1, 3], ["1", "two"])
    assert out == ["changed", "two"]
    monkeypatch.setattr(host_module._Form, "exec", lambda self: QDialog.Rejected)
    assert host.form(["A"], "T", [1], [""]) is None


def test_question_returns_the_button_pressed(host, monkeypatch):
    def press_second(self):
        self.buttons()[1].click()
        return 0

    monkeypatch.setattr(QMessageBox, "exec", press_second)
    assert host.question("Sure?", "T", ["Yes", "No", "Cancel"], "Yes") == "No"
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
    assert host.question("Sure?", "T", ["Yes", "No"], "Yes") is None


def test_messages_show_their_text_and_icon(host, monkeypatch):
    shown = []
    monkeypatch.setattr(QMessageBox, "exec", lambda self: shown.append(
        (self.text(), self.windowTitle(), self.icon())) or 0)
    host.message("error", "bad", "")
    host.message("msg", "hi", "Note")
    assert shown[0][:2] == ("bad", "Error")
    assert shown[0][2] == QMessageBox.Critical
    assert shown[1][:2] == ("hi", "Note")


def test_the_list_dialog(host, monkeypatch):
    def choose(self):
        self.list.item(1).setSelected(True)
        return QDialog.Accepted

    monkeypatch.setattr(host_module._Choice, "exec", choose)
    assert host.choose(["a", "b", "c"], "T", "p", True, [0]) == [0, 1]


def test_a_waitbar_opens_updates_and_closes(host):
    ident = host.waitbar(None, 0.25, "Working", "Progress")
    bar = host._bars[ident]
    assert bar.value() == 25 and bar.labelText() == "Working"
    assert host.waitbar(ident, 0.75, "Later", "") == ident
    assert bar.value() == 75 and bar.labelText() == "Later"
    assert host.close_waitbar(ident) is True
    assert host.close_waitbar(ident) is False


# ── the console prompt ──────────────────────────────────────────

@pytest.fixture
def console(app):
    widget = ConsoleWidget(Interpreter())
    widget.show()
    yield widget
    widget.hide()
    widget.deleteLater()


def test_read_line_takes_the_next_line_typed(app, console):
    QTimer.singleShot(20, lambda: console._submit("42"))
    assert console.read_line("n? ") == "42"
    assert console._reader is None
    assert console._prompt.text() == ">> "        # the prompt came back
    assert "n? 42" in console._transcript.toPlainText()


def test_read_line_is_not_a_command(app, console):
    ran = []
    console.executed.connect(ran.append)
    QTimer.singleShot(20, lambda: console._submit("x = 1"))
    console.read_line("")
    assert not ran and "x" not in console.interpreter.namespace


def test_stop_abandons_the_wait_with_an_interrupt(app, console):
    QTimer.singleShot(20, console.stop_requested.emit)
    with pytest.raises(Interrupted):
        console.read_line("n? ")
    assert console._reader is None


def test_input_goes_through_the_host_to_the_console(app, console):
    set_dialog_host(QtDialogs(None, console=console))
    QTimer.singleShot(20, lambda: console._submit("3*4"))
    results = console.interpreter.run_script("a = input('n? ');", "matlab")
    assert not results[0].error, results[0].error
    assert console.interpreter.namespace["a"] == 12


def test_ginput_with_no_figure_is_empty(host):
    assert host.points(2) == []
    assert host.read_line("x") is None            # no console attached


class _Click:
    """What pyqtgraph's scene hands a click handler."""

    def __init__(self, pos, button):
        self._pos, self._button = pos, button

    def scenePos(self):                                  # noqa: N802
        return self._pos

    def button(self):
        return self._button

    def accept(self):
        pass


def test_ginput_reads_clicks_in_data_coordinates(app):
    from PySide6.QtCore import Qt

    from evans.console.figures import FigureSpec
    from evans.ui.console.figure_view import FigureView

    spec = FigureSpec("xy")
    spec.add([0, 10], [0, 10], "line")
    view = FigureView(spec)
    view.resize(500, 400)
    view.show()
    app.processEvents()
    plot = view.plot_widgets()[0]
    vb = plot.plotItem.vb
    centre = vb.mapViewToScene(vb.viewRect().center())

    def click():
        plot.scene().sigMouseClicked.emit(_Click(centre, Qt.LeftButton))
        plot.scene().sigMouseClicked.emit(_Click(centre, Qt.RightButton))

    QTimer.singleShot(30, click)
    points = view.collect_points(2)
    assert [p[2] for p in points] == [1, 3]
    middle = vb.viewRect().center()
    assert points[0][0] == pytest.approx(middle.x(), abs=0.2)
    assert points[0][1] == pytest.approx(middle.y(), abs=0.2)
    view.hide()


def test_ginput_ends_on_return(app):
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from evans.console.figures import FigureSpec
    from evans.ui.console.figure_view import FigureView

    spec = FigureSpec("xy")
    spec.add([0, 1], [0, 1], "line")
    view = FigureView(spec)
    view.show()
    app.processEvents()
    QTimer.singleShot(30, lambda: QTest.keyClick(view, Qt.Key_Return))
    assert view.collect_points(None) == []
    view.hide()
