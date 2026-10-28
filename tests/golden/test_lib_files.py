"""
File I/O: delimited text, tables, fopen and friends, JSON.

Each test types the command the way a user would and checks it against a
value worked out by hand, or read back by an independent route (plain Python
``open``/``json``/``struct``), never against what Evans printed. Files are
written in pytest's ``tmp_path``, which each test ``cd``s into.
"""

from __future__ import annotations

import json
import math
import os
import struct
import sys

import numpy as np
import pytest

from evans.console import Interpreter, matlab_runtime, set_figure_sink
from evans.console.figures import recording_sink

# The library modules load through the runtime, never on their own.
_files = sys.modules[matlab_runtime.FileLibrary.__module__]
ColumnTable, make_valid_name = _files.ColumnTable, _files.make_valid_name
Cell, Struct, StructArray = (matlab_runtime.Cell, matlab_runtime.Struct,
                             matlab_runtime.StructArray)


@pytest.fixture
def it(tmp_path, monkeypatch):
    """A console whose current folder is an empty temporary one."""
    previous = set_figure_sink(recording_sink())
    monkeypatch.chdir(tmp_path)
    interp = Interpreter()
    yield interp
    interp.run_script("fclose('all');", "matlab")
    set_figure_sink(previous)


def run(it, source: str) -> str:
    """Run MATLAB, insist it succeeded; return what it printed."""
    results = it.run_script(source, "matlab")
    failed = [r for r in results if r.error]
    assert not failed, f"{failed[0].source!r} → {failed[0].error}"
    return "".join(r.output or "" for r in results)


def error_of(it, source: str) -> str:
    """Run MATLAB that must fail; return the error text."""
    results = it.run_script(source, "matlab")
    failed = [r for r in results if r.error]
    assert failed, f"{source!r} ran without an error"
    return str(failed[0].error)


def val(it, name):
    return it.namespace[name]


def write(path, text: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        fh.write(text)


def read(path) -> str:
    with open(path, newline="", encoding="utf-8") as fh:
        return fh.read()


# ──────────────────────────────────────────────────────────────
#  readmatrix
# ──────────────────────────────────────────────────────────────

def test_readmatrix_skips_a_text_header(it, tmp_path):
    """A first line of names is not data; the 2×2 numbers are as written."""
    write(tmp_path / "d.csv", "x,y\n1,2\n3,4.5\n")
    run(it, "M = readmatrix('d.csv');")
    np.testing.assert_array_equal(val(it, "M"), [[1, 2], [3, 4.5]])


@pytest.mark.parametrize("sep", ["\t", ";", "   "])
def test_readmatrix_detects_the_delimiter(it, tmp_path, sep):
    """Tab, semicolon and runs of spaces all split the same 2×3 grid."""
    write(tmp_path / "d.txt", sep.join("123") + "\n" + sep.join("456") + "\n")
    run(it, "M = readmatrix('d.txt');")
    np.testing.assert_array_equal(val(it, "M"), [[1, 2, 3], [4, 5, 6]])


def test_readmatrix_text_and_missing_fields_are_nan(it, tmp_path):
    """A word in the data and a short row both read as NaN, as MATLAB's do."""
    write(tmp_path / "d.csv", "1,abc,3\n4,5\n")
    run(it, "M = readmatrix('d.csv');")
    m = val(it, "M")
    assert m.shape == (2, 3)
    assert m[0, 0] == 1 and math.isnan(m[0, 1]) and m[0, 2] == 3
    assert m[1, 1] == 5 and math.isnan(m[1, 2])


def test_readmatrix_options(it, tmp_path):
    """NumHeaderLines skips exactly that many lines; Range 'B2:C3' is the
    lower-right 2×2 of the file's 3×3 grid."""
    write(tmp_path / "d.csv", "1,2,3\n4,5,6\n7,8,9\n")
    run(it, "A = readmatrix('d.csv', 'NumHeaderLines', 2);"
            "B = readmatrix('d.csv', 'Range', 'B2:C3');")
    np.testing.assert_array_equal(val(it, "A"), [7, 8, 9])
    np.testing.assert_array_equal(val(it, "B"), [[5, 6], [8, 9]])


def test_readmatrix_refuses_spreadsheets_and_missing_files(it, tmp_path):
    """Evans ships no openpyxl, so .xlsx is refused by name."""
    assert "openpyxl" in error_of(it, "readmatrix('d.xlsx')")
    assert "Unable to find or open" in error_of(it, "readmatrix('no.csv')")
    write(tmp_path / "d.csv", "1\n")
    assert "not supported" in error_of(it, "readmatrix('d.csv', 'Foo', 1)")


# ──────────────────────────────────────────────────────────────
#  csvread / dlmread
# ──────────────────────────────────────────────────────────────

def test_csvread_offsets_are_zero_based(it, tmp_path):
    """csvread(f, 1, 0) starts at the second line: the header is skipped.
    csvread(f, 1, 1) also drops the first column."""
    write(tmp_path / "d.csv", "a,b,c\n1,2,3\n4,5,6\n")
    run(it, "A = csvread('d.csv', 1, 0); B = csvread('d.csv', 1, 1);")
    np.testing.assert_array_equal(val(it, "A"), [[1, 2, 3], [4, 5, 6]])
    np.testing.assert_array_equal(val(it, "B"), [[2, 3], [5, 6]])


def test_csvread_range_and_empty_fields(it, tmp_path):
    """[R1 C1 R2 C2] = [0 1 1 2] is rows 1–2, columns 2–3; an empty field
    reads as 0 (dlmread's rule, unlike readmatrix's NaN)."""
    write(tmp_path / "d.csv", "1,2,3\n4,,6\n")
    run(it, "A = csvread('d.csv', 0, 0, [0 1 1 2]); B = csvread('d.csv');")
    np.testing.assert_array_equal(val(it, "A"), [[2, 3], [0, 6]])
    np.testing.assert_array_equal(val(it, "B"), [[1, 2, 3], [4, 0, 6]])


def test_csvread_refuses_text(it, tmp_path):
    """Text in the part being read is an error, as MATLAB's."""
    write(tmp_path / "d.csv", "a,b\n1,2\n")
    assert "Mismatch" in error_of(it, "A = csvread('d.csv');")


def test_dlmread_forms(it, tmp_path):
    """Auto-detected delimiter, explicit delimiter with offsets, and the
    spreadsheet range 'A2..B2' (the second row, two columns)."""
    write(tmp_path / "d.txt", "1;2;3\n4;5;6\n")
    run(it, "A = dlmread('d.txt'); B = dlmread('d.txt', ';', 1, 1);"
            "C = dlmread('d.txt', ';', 'A2..B2');")
    np.testing.assert_array_equal(val(it, "A"), [[1, 2, 3], [4, 5, 6]])
    np.testing.assert_array_equal(val(it, "B"), [5, 6])
    np.testing.assert_array_equal(val(it, "C"), [4, 5])


# ──────────────────────────────────────────────────────────────
#  writematrix / csvwrite / dlmwrite
# ──────────────────────────────────────────────────────────────

def test_writematrix_uses_long_g(it, tmp_path):
    """15 significant digits: pi is 3.14159265358979; 5 is '5', not '5.0';
    NaN is an empty field (MATLAB's documented rule)."""
    run(it, "writematrix([5 pi; NaN -0.25], 'm.csv')")
    assert read(tmp_path / "m.csv") == "5,3.14159265358979\n,-0.25\n"


def test_writematrix_default_name_delimiter_and_append(it, tmp_path):
    """No file name: the variable's name plus .txt. 'Delimiter','tab' and
    'WriteMode','append' as documented."""
    run(it, "A = [1 2]; writematrix(A)")
    assert read(tmp_path / "A.txt") == "1,2\n"
    run(it, "writematrix([3 4], 'A.txt', 'Delimiter', 'tab',"
            " 'WriteMode', 'append')")
    assert read(tmp_path / "A.txt") == "1,2\n3\t4\n"


def test_writematrix_refuses_xlsx(it):
    assert "openpyxl" in error_of(it, "writematrix([1 2], 'a.xlsx')")
    assert "writetable" in error_of(it, "writematrix({1}, 'a.csv')")


def test_writematrix_round_trips_through_readmatrix(it):
    """Write then read: 1/3 survives to 15 significant digits."""
    run(it, "A = [1/3 2; 3 4]; writematrix(A, 'r.csv'); B = readmatrix('r.csv');")
    np.testing.assert_allclose(val(it, "B"), [[1 / 3, 2], [3, 4]], rtol=1e-14)


def test_csvwrite_five_significant_digits_and_offsets(it, tmp_path):
    """csvwrite writes at most five significant digits (MATLAB's doc);
    one row offset is a line of delimiters, one column offset a leading one."""
    run(it, "csvwrite('c.csv', [pi 2], 1, 1)")
    assert read(tmp_path / "c.csv") == ",,\n,3.1416,2\n"


def test_dlmwrite_options(it, tmp_path):
    """'precision' as digits and as a format; '-append'; 'delimiter'."""
    run(it, "dlmwrite('d.txt', [pi 1], 'delimiter', ';', 'precision', 3)")
    assert read(tmp_path / "d.txt") == "3.14;1\n"
    run(it, "dlmwrite('d.txt', [2 3], '-append', 'precision', '%.2f')")
    assert read(tmp_path / "d.txt") == "3.14;1\n2.00,3.00\n"


# ──────────────────────────────────────────────────────────────
#  Tables
# ──────────────────────────────────────────────────────────────

def test_readtable_names_numbers_and_text(it, tmp_path):
    """The header names the variables; a numeric column is a double column,
    a text column a column cell of char."""
    write(tmp_path / "p.csv", "Name,Age\nSmith,38\nJones,43\n")
    run(it, "T = readtable('p.csv'); a = T.Age; n = T.Name;"
            "v = T.Properties.VariableNames; s = size(T);"
            "h = height(T); w = width(T);")
    np.testing.assert_array_equal(val(it, "a"), [[38], [43]])
    assert isinstance(val(it, "n"), Cell) and val(it, "n").dims == (2, 1)
    assert list(val(it, "n")) == ["Smith", "Jones"]
    assert list(val(it, "v")) == ["Name", "Age"] and val(it, "v").dims == (1, 2)
    np.testing.assert_array_equal(val(it, "s"), [2, 2])
    assert val(it, "h") == 2 and val(it, "w") == 2


def test_readtable_makes_valid_names_and_keeps_the_originals(it, tmp_path):
    """'first name' → firstName (space dropped, next letter capitalised);
    '2nd' → x2nd; the originals go to VariableDescriptions, with a warning."""
    write(tmp_path / "p.csv", "first name,2nd\n1,2\n")
    out = run(it, "T = readtable('p.csv'); v = T.Properties.VariableNames;"
                  "d = T.Properties.VariableDescriptions;")
    assert list(val(it, "v")) == ["firstName", "x2nd"]
    assert list(val(it, "d")) == ["first name", "2nd"]
    assert "VariableDescriptions" in out
    run(it, "P = readtable('p.csv', 'VariableNamingRule', 'preserve');"
            "q = P.Properties.VariableNames;")
    assert list(val(it, "q")) == ["first name", "2nd"]


def test_make_valid_name_rules():
    """matlab.lang.makeValidName's documented examples."""
    assert make_valid_name("Item_1") == "Item_1"
    assert make_valid_name("Another Item") == "AnotherItem"
    assert make_valid_name("case") == "xCase"
    assert make_valid_name("a-b") == "a_b"
    assert make_valid_name("") == "x"


def test_readtable_without_header_and_empty_numbers(it, tmp_path):
    """All-numeric file: Var1, Var2. An empty numeric field is NaN."""
    write(tmp_path / "n.csv", "1,2\n3,\n")
    run(it, "T = readtable('n.csv'); v = T.Properties.VariableNames;"
            "b = T.Var2;")
    assert list(val(it, "v")) == ["Var1", "Var2"]
    assert val(it, "b")[0, 0] == 2 and math.isnan(val(it, "b")[1, 0])


def test_table_row_and_variable_indexing(it):
    """T(2:3, :) keeps rows 2–3; T(:, 'b') and T(:, [2 1]) pick variables."""
    run(it, "a = [1;2;3]; b = [10;20;30];"
            "T = table(a, b, 'VariableNames', {'a', 'b'});"
            "R = T(2:3, :); r = R.b; B = T(:, 'b');"
            "S = T(:, [2 1]); n = S.Properties.VariableNames;"
            "x = T.b(2);")
    np.testing.assert_array_equal(val(it, "r"), [[20], [30]])
    assert val(it, "B").columns == ["b"]
    assert list(val(it, "n")) == ["b", "a"]
    assert val(it, "x") == 20


def test_table_refusals(it):
    """One subscript, a row-vector variable, unequal heights, unknown
    variables: MATLAB's errors, never a guess."""
    run(it, "T = table([1;2], {'p';'q'});")
    assert "one subscript" in error_of(it, "x = T(1);")
    assert "column" in error_of(it, "U = table([1 2 3]);")
    assert "same number of rows" in error_of(it, "U = table([1;2], [1;2;3]);")
    assert "Unrecognized" in error_of(it, "x = T.nope;")
    assert "Unrecognized" in error_of(it, "x = T(:, 'nope');")


def test_table_default_names_and_display(it):
    """Without names, Var1, Var2; text shows as {'p'}, as MATLAB's does."""
    out = run(it, "T = table([1;2.5], {'p';'q'})")
    t = val(it, "T")
    assert isinstance(t, ColumnTable) and t.columns == ["Var1", "Var2"]
    assert "2×2 table" in out and "{'p'}" in out and "2.5" in out


def test_array2table_and_table2array(it):
    """array2table splits the columns; table2array puts them back."""
    run(it, "A = [1 2; 3 4; 5 6];"
            "T = array2table(A, 'VariableNames', {'x', 'y'});"
            "y = T.y; B = table2array(T); U = array2table(A);"
            "u = U.Properties.VariableNames;")
    np.testing.assert_array_equal(val(it, "y"), [[2], [4], [6]])
    np.testing.assert_array_equal(val(it, "B"), [[1, 2], [3, 4], [5, 6]])
    assert list(val(it, "u")) == ["Var1", "Var2"]
    run(it, "M = table([1;2], {'a';'b'});")
    assert "Unable to concatenate" in error_of(it, "table2array(M)")


def test_writetable_round_trip(it, tmp_path):
    """Header line, then rows; text with the delimiter is quoted."""
    run(it, "T = table([1;2.5], {'a';'b,c'}, 'VariableNames', {'n', 's'});"
            "writetable(T, 't.csv'); U = readtable('t.csv'); s = U.s;")
    assert read(tmp_path / "t.csv") == 'n,s\n1,a\n2.5,"b,c"\n'
    assert list(val(it, "s")) == ["a", "b,c"]


def test_istable(it):
    run(it, "a = istable(table([1;2])); b = istable([1 2]);")
    assert val(it, "a") is True and val(it, "b") is False


# ──────────────────────────────────────────────────────────────
#  fopen, fprintf, fgetl, fscanf, textscan, fread, fwrite
# ──────────────────────────────────────────────────────────────

def test_fprintf_to_a_file(it, tmp_path):
    """fprintf(fid, ...) writes the formatted text; read back with Python."""
    run(it, "fid = fopen('o.txt', 'w');"
            "fprintf(fid, '%d,%.2f\\n', [1 2; 3 4]);"
            "fprintf(fid, 'end\\n'); fclose(fid);")
    # Column order: 1, 3 then 2, 4 (MATLAB reads the matrix down columns).
    assert read(tmp_path / "o.txt") == "1,3.00\n2,4.00\nend\n"
    assert val(it, "fid") == 3


def test_fprintf_console_forms_still_work(it):
    """fprintf(fmt, ...) and fprintf(1, fmt, ...) print to the console."""
    out = run(it, "fprintf('k = %d\\n', 3); fprintf(1, 'x = %g\\n', 2.5);")
    assert "k = 3\nx = 2.5\n" in out


def test_fprintf_returns_byte_count(it):
    """'abc\\n' is four bytes."""
    run(it, "fid = fopen('b.txt', 'w'); n = fprintf(fid, 'abc\\n'); fclose(fid);")
    assert val(it, "n") == 4


def test_fopen_append_and_failure(it, tmp_path):
    """'a' appends; a missing file gives fid -1 and the system's message."""
    write(tmp_path / "a.txt", "x\n")
    run(it, "fid = fopen('a.txt', 'a'); fprintf(fid, 'y\\n'); fclose(fid);"
            "[f, msg] = fopen('missing.txt', 'r');")
    assert read(tmp_path / "a.txt") == "x\ny\n"
    assert val(it, "f") == -1 and "No such file" in val(it, "msg")
    assert "Invalid permission" in error_of(it, "fopen('a.txt', 'q')")
    assert "Invalid file identifier" in error_of(it, "fprintf(7, 'x')")


def test_fgetl_fgets_feof(it, tmp_path):
    """fgetl drops the newline, fgets keeps it, -1 at the end of the file;
    the usual while ~feof loop reads exactly the two lines."""
    write(tmp_path / "l.txt", "one\ntwo\n")
    run(it, "fid = fopen('l.txt'); a = fgetl(fid); b = fgets(fid);"
            "c = fgetl(fid); e = feof(fid); fclose(fid);"
            "fid = fopen('l.txt'); n = 0;"
            "while ~feof(fid), fgetl(fid); n = n + 1; end; fclose(fid);")
    assert val(it, "a") == "one" and val(it, "b") == "two\n"
    assert val(it, "c") == -1 and val(it, "e") is True and val(it, "n") == 2


def test_ftell_fseek_frewind(it, tmp_path):
    """Byte positions: after 'abc\\n' ftell is 4; fseek(-2, 'eof') lands on
    the last line's second-to-last byte."""
    write(tmp_path / "s.txt", "abc\nxyz\n")
    run(it, "fid = fopen('s.txt'); fgetl(fid); p = ftell(fid);"
            "st = fseek(fid, -3, 'eof'); t = fgetl(fid);"
            "frewind(fid); u = fgetl(fid); bad = fseek(fid, -1, 'bof');"
            "fclose(fid);")
    assert val(it, "p") == 4 and val(it, "st") == 0
    assert val(it, "t") == "yz" and val(it, "u") == "abc"
    assert val(it, "bad") == -1


def test_fscanf_fills_column_wise(it, tmp_path):
    """sizeA [2 Inf] reads 1..6 down columns: [1 3 5; 2 4 6]."""
    write(tmp_path / "n.txt", "1 2 3\n4 5 6\n")
    run(it, "fid = fopen('n.txt'); [A, n] = fscanf(fid, '%d', [2 Inf]);"
            "fclose(fid); fid = fopen('n.txt'); B = fscanf(fid, '%f');"
            "fclose(fid); fid = fopen('n.txt'); C = fscanf(fid, '%d', 4);"
            "fclose(fid);")
    np.testing.assert_array_equal(val(it, "A"), [[1, 3, 5], [2, 4, 6]])
    assert val(it, "n") == 6
    np.testing.assert_array_equal(val(it, "B"), np.arange(1, 7).reshape(-1, 1))
    np.testing.assert_array_equal(val(it, "C"), [[1], [2], [3], [4]])


def test_fscanf_literals_and_text(it, tmp_path):
    """Literal text in the format is matched and skipped; %s alone gives
    char, with no spaces between the words (MATLAB concatenates)."""
    write(tmp_path / "k.txt", "x=1.5 x=2.5\n")
    write(tmp_path / "w.txt", "ab cd\n")
    run(it, "fid = fopen('k.txt'); A = fscanf(fid, 'x=%f '); fclose(fid);"
            "fid = fopen('w.txt'); s = fscanf(fid, '%s'); fclose(fid);")
    np.testing.assert_array_equal(val(it, "A"), [[1.5], [2.5]])
    assert val(it, "s") == "abcd"


def test_textscan_columns(it, tmp_path):
    """'%s %f' over two lines: a 1×2 cell of a text column and a number
    column; HeaderLines skips the first line."""
    write(tmp_path / "t.txt", "name value\nalpha 1.5\nbeta 2\n")
    run(it, "fid = fopen('t.txt');"
            "C = textscan(fid, '%s %f', 'HeaderLines', 1); fclose(fid);"
            "a = C{1}; b = C{2};")
    c = val(it, "C")
    assert isinstance(c, Cell) and c.dims == (1, 2)
    assert list(val(it, "a")) == ["alpha", "beta"] and val(it, "a").dims == (2, 1)
    np.testing.assert_array_equal(val(it, "b"), [[1.5], [2]])


def test_textscan_delimiter_and_empty_fields(it, tmp_path):
    """With 'Delimiter', ',' a name may hold spaces, and an empty number
    field is NaN."""
    write(tmp_path / "c.csv", "New York,3\nParis,\n")
    run(it, "fid = fopen('c.csv');"
            "C = textscan(fid, '%s %f', 'Delimiter', ','); fclose(fid);"
            "a = C{1}; b = C{2};")
    assert list(val(it, "a")) == ["New York", "Paris"]
    b = val(it, "b")
    assert b[0, 0] == 3 and math.isnan(b[1, 0])


def test_textscan_from_text_and_repeat_count(it):
    """textscan also reads a char vector; N = 2 reads the format twice."""
    run(it, "C = textscan('1 2 3 4 5 6', '%f %f', 2); a = C{1}; b = C{2};")
    np.testing.assert_array_equal(val(it, "a"), [[1], [3]])
    np.testing.assert_array_equal(val(it, "b"), [[2], [4]])


def test_fwrite_and_fread_binary(it, tmp_path):
    """int16 little-endian values, checked with Python's struct; doubles
    read back exactly; fread's default uint8 sees the raw bytes."""
    run(it, "fid = fopen('b.bin', 'w'); n = fwrite(fid, [1 -2 300], 'int16');"
            "fwrite(fid, pi, 'double'); fclose(fid);"
            "fid = fopen('b.bin'); a = fread(fid, 3, 'int16');"
            "p = fread(fid, 1, 'double'); fclose(fid);"
            "fid = fopen('b.bin'); [u, k] = fread(fid, [2 2]); fclose(fid);")
    raw = (tmp_path / "b.bin").read_bytes()
    assert struct.unpack("<3hd", raw) == (1, -2, 300, math.pi)
    assert val(it, "n") == 3
    np.testing.assert_array_equal(val(it, "a"), [[1], [-2], [300]])
    assert val(it, "p") == math.pi
    np.testing.assert_array_equal(val(it, "u"), [[raw[0], raw[2]],
                                                 [raw[1], raw[3]]])
    assert val(it, "k") == 4


def test_fwrite_saturates_and_char(it, tmp_path):
    """uint8 clips 300 to 255 and -1 to 0, rounds 2.5 to 3 (half away from
    zero); a char vector writes its codes; '*char' reads text back."""
    run(it, "fid = fopen('c.bin', 'w'); fwrite(fid, [300 -1 2.5]);"
            "fwrite(fid, 'hi'); fclose(fid);"
            "fid = fopen('c.bin'); fread(fid, 3); s = fread(fid, '*char');"
            "fclose(fid);")
    assert (tmp_path / "c.bin").read_bytes() == bytes([255, 0, 3]) + b"hi"
    assert val(it, "s") == "hi"
    assert "double" in error_of(it, "fid = fopen('c.bin'); "
                                    "x = fread(fid, '*int16');")


def test_fclose_all(it):
    """fclose('all') closes every file; the fid is invalid afterwards."""
    run(it, "f1 = fopen('a.txt', 'w'); f2 = fopen('b.txt', 'w');"
            "fclose('all'); o = fopen('all');")
    assert val(it, "f1") == 3 and val(it, "f2") == 4
    assert np.size(val(it, "o")) == 0
    assert "Invalid file identifier" in error_of(it, "fclose(f1)")


# ──────────────────────────────────────────────────────────────
#  JSON
# ──────────────────────────────────────────────────────────────

def test_jsondecode_mapping(it):
    """MATLAB's mapping: number arrays → columns, nested equal arrays → a
    matrix (inner arrays are rows), mixed → column cell, null → [],
    true → logical, null inside numbers → NaN."""
    run(it, "a = jsondecode('[1,2,3]'); m = jsondecode('[[1,2],[3,4]]');"
            "c = jsondecode('[1,\"x\"]'); z = jsondecode('null');"
            "t = jsondecode('true'); n = jsondecode('[1,null]');"
            "b = jsondecode('[true,false]'); s = jsondecode('\"hi\"');")
    np.testing.assert_array_equal(val(it, "a"), [[1], [2], [3]])
    np.testing.assert_array_equal(val(it, "m"), [[1, 2], [3, 4]])
    assert val(it, "c").dims == (2, 1) and list(val(it, "c")) == [1, "x"]
    assert np.size(val(it, "z")) == 0
    assert val(it, "t") is True
    assert val(it, "n")[0, 0] == 1 and math.isnan(val(it, "n")[1, 0])
    assert val(it, "b").dtype == bool and val(it, "b").shape == (2, 1)
    assert val(it, "s") == "hi"


def test_jsondecode_objects(it):
    """Objects → structs with valid field names; an array of objects with
    the same fields → a 2×1 struct array; differing fields → a cell."""
    run(it, "s = jsondecode('{\"a b\":1,\"c\":{\"d\":[]}}');"
            "r = jsondecode('[{\"p\":1},{\"p\":2}]'); q = r(2).p;"
            "k = jsondecode('[{\"p\":1},{\"q\":2}]');")
    s = val(it, "s")
    assert isinstance(s, Struct) and list(s) == ["aB", "c"] and s["aB"] == 1
    assert isinstance(val(it, "r"), StructArray)
    assert val(it, "r").dims == (2, 1) and val(it, "q") == 2
    assert isinstance(val(it, "k"), Cell) and val(it, "k").dims == (2, 1)
    assert "JSON syntax error" in error_of(it, "jsondecode('{bad')")


def test_jsonencode_mapping(it):
    """Rows and columns are both arrays; a matrix is row-major nested;
    NaN → null; logical → true/false; parsed back with Python's json."""
    run(it, "a = jsonencode([1 2 3]); b = jsonencode([1;2;3]);"
            "m = jsonencode([1 2; 3 4]); n = jsonencode([1 NaN Inf]);"
            "l = jsonencode(true); s = jsonencode(struct('x', 1.5, 'y', 'hi'));"
            "c = jsonencode({1, 'a', [1 2]}); e = jsonencode([]);")
    assert val(it, "a") == "[1,2,3]" and val(it, "b") == "[1,2,3]"
    assert val(it, "m") == "[[1,2],[3,4]]"
    assert val(it, "n") == "[1,null,null]"
    assert val(it, "l") == "true"
    assert json.loads(val(it, "s")) == {"x": 1.5, "y": "hi"}
    assert json.loads(val(it, "c")) == [1, "a", [1, 2]]
    assert val(it, "e") == "[]"


def test_jsonencode_pretty_and_round_trip(it):
    """PrettyPrint puts each member on its own line; decode(encode(x)) == x
    for a struct of a scalar and a vector."""
    run(it, "p = jsonencode(struct('a', 1), 'PrettyPrint', true);"
            "s = jsondecode(jsonencode(struct('k', 2, 'v', [1 2 3])));")
    assert val(it, "p") == '{\n  "a": 1\n}'
    s = val(it, "s")
    assert s["k"] == 2
    np.testing.assert_array_equal(s["v"], [[1], [2], [3]])
    assert "complex" in error_of(it, "jsonencode(1+2i)")


def test_files_follow_cd(it, tmp_path):
    """Every file name is resolved against MATLAB's current folder."""
    sub = tmp_path / "sub"
    sub.mkdir()
    run(it, "cd sub\nwritematrix([7 8], 'z.csv')")
    assert os.path.exists(sub / "z.csv")
