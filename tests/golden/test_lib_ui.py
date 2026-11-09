"""
Dialogs and the console prompt: uigetfile, uiputfile, uigetdir, inputdlg,
questdlg, listdlg, msgbox and its siblings, waitbar, ginput, input, keyboard.

The commands only ask the installed host (``evans.console.dialogs``), so these
tests install a scripted one: no window ever opens. The Qt host is tested
separately in ``test_dialog_host.py``.
"""

from __future__ import annotations

import os

import numpy as np
import pytest

from evans.console import Interpreter, set_figure_sink
from evans.console import matlab_runtime as _mr  # noqa: F401
from evans.console.dialogs import (
    dialog_host,
    scripted_host,
    set_dialog_host,
)
from evans.console.figures import recording_sink
from evans.console.matlab_runtime import Cell


@pytest.fixture
def it():
    previous = set_figure_sink(recording_sink())
    yield Interpreter()
    set_figure_sink(previous)


@pytest.fixture
def host():
    fresh = scripted_host()
    previous = set_dialog_host(fresh)
    yield fresh
    set_dialog_host(previous)


def run(it, source: str):
    results = it.run_script(source, "matlab")
    failed = [r for r in results if r.error]
    assert not failed, f"{failed[0].source!r} → {failed[0].error}"
    return results


def error_of(it, source: str) -> str:
    results = it.run_script(source, "matlab")
    failed = [r for r in results if r.error]
    assert failed, f"{source!r} should have failed"
    return failed[0].error


def value(it, name: str):
    return it.namespace[name]


def path(*parts: str) -> str:
    return os.path.join(os.path.abspath(os.sep), *parts)


# ── files and folders ─────────────────────────────────────────────

def test_uigetfile_returns_name_path_and_filter_index(it, host):
    host.queue("open_files", [path("data", "run1.csv")])
    run(it, "[f, p, i] = uigetfile({'*.m', 'Code'; '*.csv;*.txt', 'Data'});")
    assert value(it, "f") == "run1.csv"
    assert value(it, "p") == path("data") + os.sep
    assert value(it, "i") == 2
    title, filters, start, multiple = host.asked("open_files")[0]
    assert filters == [("*.m", "Code"), ("*.csv;*.txt", "Data")]
    assert multiple is False


def test_uigetfile_cancel_gives_zeros(it, host):
    run(it, "[f, p, i] = uigetfile('*.m');")
    assert (value(it, "f"), value(it, "p"), value(it, "i")) == (0, 0, 0)
    run(it, "g = uigetfile;")
    assert value(it, "g") == 0


def test_uigetfile_multiselect_returns_a_cell_of_names(it, host):
    host.queue("open_files", [path("d", "a.m"), path("d", "b.m")])
    run(it, "f = uigetfile('*.m', 'Pick', 'MultiSelect', 'on');")
    assert isinstance(value(it, "f"), Cell)
    assert list(value(it, "f")) == ["a.m", "b.m"]
    assert host.asked("open_files")[0][0] == "Pick"
    assert host.asked("open_files")[0][3] is True


def test_uigetfile_defaults_to_all_files_and_starts_in_the_given_folder(
        it, host, tmp_path):
    run(it, f"f = uigetfile('', 'T', '{tmp_path.as_posix()}/');")
    _, filters, start, _ = host.asked("open_files")[0]
    assert filters == [("*.*", "All Files (*.*)")]
    assert os.path.samefile(start, tmp_path)


def test_uiputfile_offers_a_name_and_returns_the_pick(it, host):
    host.queue("save_file", path("out", "result.mat"))
    run(it, "[f, p] = uiputfile('*.mat');")
    assert value(it, "f") == "result.mat"
    assert value(it, "p") == path("out") + os.sep
    assert host.asked("save_file")[0][2].endswith("Untitled.mat")


def test_uiputfile_cancel(it, host):
    run(it, "f = uiputfile('*.mat', 'Save', 'x.mat');")
    assert value(it, "f") == 0
    assert host.asked("save_file")[0][2].endswith("x.mat")


def test_uigetdir(it, host):
    host.queue("directory", path("some", "dir"))
    run(it, "d = uigetdir; e = uigetdir;")
    assert value(it, "d") == path("some", "dir")
    assert value(it, "e") == 0


# ── text input, questions, lists ──────────────────────────────────

def test_inputdlg_returns_a_column_cell_of_text(it, host):
    host.queue("form", ["2.5", "abc"])
    run(it, "a = inputdlg({'Gain', 'Name'}, 'Setup', [1 30], {'1', 'x'});")
    a = value(it, "a")
    assert isinstance(a, Cell) and a.dims == (2, 1)
    assert list(a) == ["2.5", "abc"]
    prompts, title, lines, defaults = host.asked("form")[0]
    assert prompts == ["Gain", "Name"] and title == "Setup"
    assert defaults == ["1", "x"] and lines == [1, 1]


def test_inputdlg_cancel_is_an_empty_cell(it, host):
    run(it, "a = inputdlg('Value'); e = isempty(a);")
    assert value(it, "e")
    assert host.asked("form")[0][0] == ["Value"]


def test_inputdlg_default_count_must_match(it, host):
    assert "default" in error_of(it, "inputdlg({'a', 'b'}, 't', 1, {'x'});")


def test_questdlg_default_buttons(it, host):
    host.queue("question", "No")
    run(it, "a = questdlg('Sure?');")
    assert value(it, "a") == "No"
    _, _, buttons, default = host.asked("question")[0]
    assert buttons == ["Yes", "No", "Cancel"] and default == "Yes"


def test_questdlg_custom_buttons_and_default(it, host):
    host.queue("question", "Keep")
    run(it, "a = questdlg('Overwrite?', 'File', 'Replace', 'Keep', 'Keep');")
    assert value(it, "a") == "Keep"
    _, title, buttons, default = host.asked("question")[0]
    assert (title, buttons, default) == ("File", ["Replace", "Keep"], "Keep")


def test_questdlg_closed_window_is_empty_text(it, host):
    run(it, "a = questdlg('Q?', 'T', 'A', 'B', 'A');")
    assert value(it, "a") == ""


def test_questdlg_default_must_be_a_button(it, host):
    assert "default" in error_of(it, "questdlg('Q', 'T', 'Maybe');")


def test_listdlg_returns_positions_and_ok(it, host):
    host.queue("choose", [2, 0])
    run(it, "[k, ok] = listdlg('ListString', {'a', 'b', 'c'}, "
            "'PromptString', 'Pick');")
    assert np.asarray(value(it, "k")).reshape(-1).tolist() == [1, 3]
    assert value(it, "ok") == 1
    items, _, prompt, multiple, _ = host.asked("choose")[0]
    assert items == ["a", "b", "c"] and prompt == "Pick" and multiple


def test_listdlg_cancel_and_single_mode(it, host):
    run(it, "[k, ok] = listdlg('ListString', {'a'}, 'SelectionMode', "
            "'single');")
    assert value(it, "ok") == 0 and np.size(value(it, "k")) == 0
    assert host.asked("choose")[0][3] is False


# ── message boxes and the waitbar ────────────────────────────────

def test_message_boxes_pass_their_kind_text_and_title(it, host):
    run(it, "msgbox('hello'); msgbox({'a', 'b'}, 'T', 'warn'); "
            "errordlg('bad'); warndlg('careful', 'W'); helpdlg('how');")
    kinds = [(k, t, ti) for k, t, ti in host.asked("message")]
    assert kinds == [("msg", "hello", ""), ("warn", "a\nb", "T"),
                     ("error", "bad", "Error Dialog"),
                     ("warn", "careful", "W"), ("help", "how", "Help Dialog")]


def test_a_message_box_returns_a_handle_only_when_asked(it, host):
    results = run(it, "msgbox('x');")
    assert results[0].display() == ""
    run(it, "h = msgbox('x');")
    assert value(it, "h") != 0


def test_waitbar_opens_updates_and_closes(it, host):
    run(it, "h = waitbar(0, 'Working'); waitbar(0.5, h, 'Half'); "
            "waitbar(1, h); close(h);")
    names = [name for name, _ in host.calls]
    assert names == ["waitbar", "waitbar", "waitbar", "close_waitbar"]
    assert host.calls[1][1][1:3] == (0.5, "Half")
    assert not host.waitbars


def test_delete_closes_a_waitbar_too(it, host):
    run(it, "h = waitbar(0.1); delete(h);")
    assert not host.waitbars


def test_waitbar_fraction_must_be_between_zero_and_one(it, host):
    assert "between 0 and 1" in error_of(it, "waitbar(2);")


def test_close_still_closes_figures(it, host):
    run(it, "plot(1:3); close all")             # no error, no waitbar call
    assert not host.asked("close_waitbar")


# ── ginput ────────────────────────────────────────────────────────

def test_ginput_two_outputs(it, host):
    host.queue("points", [(1.5, 2.5, 1), (3.0, 4.0, 3)])
    run(it, "[x, y, b] = ginput(2);")
    assert np.asarray(value(it, "x")).reshape(-1).tolist() == [1.5, 3.0]
    assert np.asarray(value(it, "y")).reshape(-1).tolist() == [2.5, 4.0]
    assert np.asarray(value(it, "b")).reshape(-1).tolist() == [1, 3]
    assert host.asked("points")[0] == (2,)


def test_ginput_one_output_is_an_n_by_two_matrix(it, host):
    host.queue("points", [(1.0, 2.0, 1), (3.0, 4.0, 1)])
    run(it, "xy = ginput(2);")
    assert value(it, "xy").tolist() == [[1, 2], [3, 4]]


def test_ginput_with_no_clicks_is_empty(it, host):
    run(it, "xy = ginput(3); n = size(xy, 1);")
    assert value(it, "n") == 0


# ── input and keyboard ───────────────────────────────────────────

def test_input_evaluates_what_is_typed(it, host):
    host.queue("read_line", "2*pi", "[1 2 3]")
    run(it, "a = input('x? '); b = input('v? ');")
    assert value(it, "a") == pytest.approx(2 * np.pi)
    assert value(it, "b").tolist() == [1, 2, 3]
    assert [c[0] for c in host.asked("read_line")] == ["x? ", "v? "]


def test_input_can_read_a_workspace_variable(it, host):
    host.queue("read_line", "k + 1")
    run(it, "k = 4; a = input('');")
    assert value(it, "a") == 5


def test_input_s_returns_the_text_untouched(it, host):
    host.queue("read_line", "2*pi", "")
    run(it, "a = input('name: ', 's'); b = input('again: ', 's');")
    assert value(it, "a") == "2*pi" and value(it, "b") == ""


def test_input_of_nothing_is_empty(it, host):
    host.queue("read_line", "")
    run(it, "a = input('');")
    assert np.size(value(it, "a")) == 0


def test_input_without_a_keyboard_is_a_catchable_error(it, host):
    assert "needs a keyboard" in error_of(it, "input('x');")
    run(it, "try, a = input('x'); catch, a = 9; end")
    assert value(it, "a") == 9


def test_keyboard_runs_lines_until_return(it, host):
    host.queue("read_line", "q = 5;", "r = q * 2", "return")
    results = run(it, "keyboard\ndisp(q + r)")
    assert value(it, "q") == 5 and value(it, "r") == 10
    assert "15" in results[-1].display()


def test_keyboard_survives_an_error_in_a_typed_line(it, host):
    host.queue("read_line", "nosuchthing", "z = 1;", "dbcont")
    results = run(it, "keyboard")
    assert "Unrecognized" in results[0].display()
    assert value(it, "z") == 1


def test_keyboard_without_a_keyboard_is_an_error(it, host):
    assert "needs a keyboard" in error_of(it, "keyboard")


def test_the_default_host_answers_cancel(it):
    assert type(dialog_host()).__name__ == "ScriptedDialogs"
    run(it, "f = uigetfile; a = inputdlg('x'); q = questdlg('?');")
    assert value(it, "f") == 0 and value(it, "q") == ""
