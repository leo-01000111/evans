"""
Workspace and system helpers, dates, and number functions.

Each test types the command as a user would, at the MATLAB console, and
checks it against a value worked out by hand, from a closed form, or by an
independent route (Python's ``datetime``, ``math``, a different formula),
never against what Evans printed.
"""

from __future__ import annotations

import datetime as dt
import math
import os
import time

import numpy as np
import pytest

from evans.console import Interpreter, matlab_runtime, set_figure_sink
from evans.console.figures import recording_sink
from evans.console.matlab_runtime import Cell, StructArray


@pytest.fixture
def it():
    previous = set_figure_sink(recording_sink())
    yield Interpreter()
    set_figure_sink(previous)


def run(it, source: str, folder=None) -> str:
    """Run MATLAB, insist it succeeded; return what it printed."""
    results = it.run_script(source, "matlab",
                            folder=None if folder is None else str(folder))
    failed = [r for r in results if r.error]
    assert not failed, f"{failed[0].source!r} → {failed[0].error}"
    return "\n".join(r.output for r in results)


def error_of(it, source: str, folder=None) -> str:
    """Run MATLAB that must fail; return the error text."""
    results = it.run_script(source, "matlab",
                            folder=None if folder is None else str(folder))
    failed = [r for r in results if r.error]
    assert failed, f"{source!r} ran without an error"
    return str(failed[0].error)


def val(it, name):
    return it.namespace[name]


def matlab_datenum(*parts) -> float:
    """Independent route: Python's proleptic ordinal, + 366 for year 0."""
    y, mo, d, *hms = parts + (0,) * (6 - len(parts))
    h, mi, s = hms[:3]
    return dt.date(y, mo, d).toordinal() + 366 + (h * 3600 + mi * 60 + s) \
        / 86400


# ──────────────────────────────────────────────────────────────
#  who, whos, which, exist
# ──────────────────────────────────────────────────────────────

def test_who_lists_only_the_users_variables_sorted(it):
    """The console presets (``s``, ``pi``, ``tf``) are not user variables."""
    out = run(it, "b = 2; a = 1; Z = 'x';\nwho")
    assert "Your variables are:" in out
    assert out.split("Your variables are:")[1].split() == ["Z", "a", "b"]


def test_who_returns_a_column_cell_and_takes_patterns(it):
    run(it, "alpha = 1; beta2 = 2; gamma3 = 3; c = who('a*', 'g*');")
    c = val(it, "c")
    assert isinstance(c, Cell) and c.dims == (2, 1)
    assert list(c) == ["alpha", "gamma3"]
    out = run(it, "who alpha")
    assert out.split("Your variables are:")[1].split() == ["alpha"]


def test_who_inside_a_function_sees_its_locals(it, tmp_path):
    """A function's workspace is its own: its inputs and locals only."""
    (tmp_path / "probe.m").write_text(
        "function c = probe(x)\nlocal1 = 2;\nc = who;\nend\n")
    run(it, "outer = 1; c = probe(5);", tmp_path)
    assert list(val(it, "c")) == ["local1", "x"]


def test_whos_counts_bytes_as_matlab_does(it):
    """8 per double, 16 per complex double, 2 per char, 1 per logical."""
    out = run(it, "A = zeros(3,4); z = [1+2i 3]; s = 'hello'; "
                  "L = [1 2 3] > 1;\nwhos")
    rows = {line.split()[0]: line.split() for line in out.splitlines()
            if line.strip() and not line.strip().startswith("Name")}
    assert rows["A"][1:4] == ["3x4", "96", "double"]
    assert rows["z"][1:5] == ["1x2", "32", "double", "complex"]
    assert rows["s"][1:4] == ["1x5", "10", "char"]
    assert rows["L"][1:4] == ["1x3", "3", "logical"]


def test_whos_returns_a_column_struct_array(it):
    run(it, "q = [1 2 3]; p = 'ab'; w = whos; n = w(2).name; "
            "sz = w(2).size; b = w(1).bytes; k = w(1).class;")
    w = val(it, "w")
    assert isinstance(w, StructArray) and w.dims == (2, 1)
    assert val(it, "n") == "q"                 # sorted: p, q
    np.testing.assert_array_equal(np.ravel(val(it, "sz")), [1, 3])
    assert (val(it, "b"), val(it, "k")) == (4, "char")


def test_which_names_variables_files_and_builtins(it, tmp_path):
    (tmp_path / "triple.m").write_text("function y = triple(x)\ny = 3*x;\n"
                                       "end\n")
    out = run(it, "x = 1;\nwhich x\nwhich sin\nwhich nothere", tmp_path)
    assert "x is a variable." in out
    assert "built-in (Evans)" in out
    assert "'nothere' not found." in out
    run(it, "p = which('triple'); q = which('nope'); v = which('x');",
        tmp_path)
    assert val(it, "p") == str(tmp_path / "triple.m")
    assert (val(it, "q"), val(it, "v")) == ("", "variable")
    assert "-all" in error_of(it, "which -all sin")


def test_exist_codes_and_search_types(it, tmp_path):
    """1 variable, 2 file, 5 built-in, 7 folder, 0 nothing."""
    (tmp_path / "sub").mkdir()
    (tmp_path / "notes.txt").write_text("hi")
    run(it, "v = 3;\n"
            "e = [exist('v') exist('notes.txt') exist('sin') exist('sub') "
            "exist('nope')];\n"
            "f = [exist('v','var') exist('sin','var') exist('sub','dir') "
            "exist('notes.txt','file') exist('sub','file') "
            "exist('sin','builtin') exist('v','builtin')];", tmp_path)
    np.testing.assert_array_equal(val(it, "e"), [1, 2, 5, 7, 0])
    np.testing.assert_array_equal(val(it, "f"), [1, 0, 7, 2, 7, 5, 0])


def test_exist_does_not_count_console_presets(it):
    """``s`` is preset for transfer functions; a fresh MATLAB has no ``s``."""
    run(it, "e = exist('s');")
    assert val(it, "e") == 0
    assert "Invalid search type" in error_of(it, "exist('x', 'nope')")


# ──────────────────────────────────────────────────────────────
#  Files and folders
# ──────────────────────────────────────────────────────────────

def test_dir_returns_an_n_by_1_struct_array(it, tmp_path):
    (tmp_path / "a.csv").write_text("12345")
    (tmp_path / "b.csv").write_text("1")
    (tmp_path / "c.txt").write_text("")
    run(it, "d = dir('*.csv'); n = d(1).name; b = d(1).bytes; "
            "f = d(2).folder; k = d(1).isdir; dn = d(1).datenum;", tmp_path)
    d = val(it, "d")
    assert isinstance(d, StructArray) and d.dims == (2, 1)
    assert (val(it, "n"), val(it, "b"), val(it, "k")) == ("a.csv", 5, False)
    assert val(it, "f") == str(tmp_path)
    stamp = dt.datetime.fromtimestamp(os.stat(tmp_path / "a.csv").st_mtime)
    assert val(it, "dn") == pytest.approx(matlab_datenum(
        stamp.year, stamp.month, stamp.day, stamp.hour, stamp.minute,
        stamp.second + stamp.microsecond / 1e6), abs=1e-8)


def test_dir_as_a_command_prints_names_with_dots(it, tmp_path):
    (tmp_path / "data1.csv").write_text("")
    (tmp_path / "sub").mkdir()
    out = run(it, "dir", tmp_path)
    assert out.split() == [".", "..", "data1.csv", "sub"]
    assert run(it, "dir data*.csv", tmp_path).split() == ["data1.csv"]
    assert run(it, "ls", tmp_path).split() == [".", "..", "data1.csv", "sub"]


def test_dir_recursive_pattern(it, tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "top.m").write_text("")
    (tmp_path / "sub" / "deep.m").write_text("")
    run(it, "d = dir('**/*.m'); n = numel(d);", tmp_path)
    assert val(it, "n") == 2


def test_delete_with_wildcards_refuses_folders(it, tmp_path):
    for name in ("x1.tmp", "x2.tmp", "keep.txt"):
        (tmp_path / name).write_text("")
    (tmp_path / "folder").mkdir()
    run(it, "delete('*.tmp')", tmp_path)
    assert sorted(os.listdir(tmp_path)) == ["folder", "keep.txt"]
    out = run(it, "delete nothere.txt", tmp_path)
    assert "Warning: File 'nothere.txt' not found." in out
    assert "rmdir" in error_of(it, "delete folder", tmp_path)


def test_copyfile_movefile_with_status(it, tmp_path):
    (tmp_path / "a.txt").write_text("abc")
    (tmp_path / "dest").mkdir()
    run(it, "copyfile('a.txt', 'dest');\n[s1, m1] = copyfile('a.txt', "
            "'b.txt');\nmovefile('b.txt', 'c.txt');\n"
            "[s2, m2] = movefile('nope.txt', 'd.txt');", tmp_path)
    assert (tmp_path / "dest" / "a.txt").read_text() == "abc"
    assert (tmp_path / "c.txt").read_text() == "abc"
    assert not (tmp_path / "b.txt").exists()
    assert (val(it, "s1"), val(it, "m1")) == (True, "")
    assert val(it, "s2") is False and "No matching files" in val(it, "m2")
    assert "No matching files" in error_of(it, "copyfile('zz.txt', 'q.txt')",
                                           tmp_path)


def test_mkdir_forms_and_rmdir(it, tmp_path):
    out = run(it, "mkdir sub\nmkdir('sub', 'inner')\n[s, m] = mkdir('sub');",
              tmp_path)
    assert (tmp_path / "sub" / "inner").is_dir()
    assert out.strip() == ""                       # mkdir says nothing
    assert (val(it, "s"), val(it, "m")) == (True, "Directory already exists.")
    assert "Directory already exists" in run(it, "mkdir sub", tmp_path)
    assert "not empty" in error_of(it, "rmdir sub", tmp_path)
    run(it, "[ok, msg] = rmdir('nope');", tmp_path)
    assert val(it, "ok") is False
    run(it, "rmdir sub s", tmp_path)
    assert not (tmp_path / "sub").exists()


def test_system_runs_in_the_current_folder(it, tmp_path):
    (tmp_path / "marker_file.txt").write_text("")
    cmd = "dir /b" if os.name == "nt" else "ls"
    run(it, f"[st, out] = system('{cmd}');", tmp_path)
    assert val(it, "st") == 0
    assert "marker_file.txt" in val(it, "out")
    out = run(it, "system('echo hello')", tmp_path)
    assert "hello" in out and "ans = 0" in out
    run(it, "[st2, o2] = system('exit 3');", tmp_path)
    assert val(it, "st2") == 3


def test_getenv_setenv_and_platform(it, monkeypatch):
    monkeypatch.delenv("EVANS_TEST_VAR", raising=False)
    run(it, "a = getenv('EVANS_TEST_VAR'); setenv('EVANS_TEST_VAR', 'on'); "
            "b = getenv('EVANS_TEST_VAR'); p = ispc; u = isunix;")
    assert (val(it, "a"), val(it, "b")) == ("", "on")
    assert val(it, "p") is (os.name == "nt")
    assert val(it, "u") is (os.name != "nt")
    os.environ.pop("EVANS_TEST_VAR", None)


# ──────────────────────────────────────────────────────────────
#  pause and Stop
# ──────────────────────────────────────────────────────────────

def test_pause_off_skips_later_pauses(it, monkeypatch):
    waited = []
    monkeypatch.setattr(matlab_runtime, "_pause_for", waited.append)
    run(it, "pause(0.2)\npause off\npause(3)\nq = pause('query');\n"
            "pause on\npause(0.1)")
    assert waited == [0.2, 0.1]
    assert val(it, "q") == "off"


def test_stop_ends_a_pause_promptly(it):
    """The Stop button is polled while pause waits: a 30 s pause ends now."""
    calls = []

    def poll():
        calls.append(1)
        if len(calls) == 3:
            it.tracer.request_stop()

    it.tracer.poll = poll
    start = time.monotonic()
    results = it.run_script("pause(30)\nx = 1;", "matlab")
    assert time.monotonic() - start < 5
    assert any(r.error and "Interrupted" in r.error for r in results)
    assert "x" not in it.namespace


def test_a_real_pause_waits(it):
    start = time.monotonic()
    run(it, "pause(0.2)")
    assert time.monotonic() - start >= 0.19


# ──────────────────────────────────────────────────────────────
#  Dates
# ──────────────────────────────────────────────────────────────

def test_datenum_from_numbers_vectors_and_strings(it):
    """1-Jan-2000 is day 730486: 730120 days of years 0..1999 + 366."""
    run(it, "a = datenum(2000,1,1); b = datenum([2026 10 28 14 5 9]); "
            "c = datenum('28-Oct-2026 14:05:09'); d = datenum('2026-10-28'); "
            "e = datenum(2000, 13, 1); f = datenum([2000 1 1; 2000 3 1]); "
            "g = datenum('03/01/2000');")
    assert val(it, "a") == 730486
    assert val(it, "b") == pytest.approx(matlab_datenum(2026, 10, 28, 14, 5,
                                                        9), abs=1e-9)
    assert val(it, "c") == pytest.approx(val(it, "b"), abs=1e-9)
    assert val(it, "d") == matlab_datenum(2026, 10, 28)
    assert val(it, "e") == matlab_datenum(2001, 1, 1)        # month 13
    np.testing.assert_array_equal(val(it, "f"), [[730486], [730546]])
    assert val(it, "g") == matlab_datenum(2000, 3, 1)


def test_datenum_matches_ordinals_across_leap_rules(it):
    """1900 is not a leap year, 2000 is: checked against ``toordinal``."""
    for y, m, d in [(1900, 3, 1), (2000, 2, 29), (2000, 3, 1), (1, 1, 1),
                    (2100, 12, 31)]:
        run(it, f"n = datenum({y}, {m}, {d});")
        assert val(it, "n") == matlab_datenum(y, m, d), (y, m, d)


def test_datestr_formats(it):
    run(it, "n = datenum(2026,10,28,14,5,9);\n"
            "a = datestr(n); b = datestr(730486); c = datestr(n, 'yyyy-mm-dd');"
            " d = datestr(n, 'HH:MM:SS'); e = datestr(n, 1); f = datestr(n, 31);"
            " g = datestr(n, 'dddd mmm dd, HH:MM PM'); h = datestr(n, 29);"
            " k = datestr([2000 1 1 12 0 0]);")
    assert val(it, "a") == "28-Oct-2026 14:05:09"
    assert val(it, "b") == "01-Jan-2000"          # midnight: format 1
    assert val(it, "c") == "2026-10-28"
    assert val(it, "d") == "14:05:09"
    assert val(it, "e") == "28-Oct-2026"
    assert val(it, "f") == "2026-10-28 14:05:09"
    # 28 Oct 2026 is a Wednesday (datetime's weekday is independent).
    assert dt.date(2026, 10, 28).strftime("%A") == "Wednesday"
    assert val(it, "g") == "Wednesday Oct 28, 02:05 PM"
    assert val(it, "h") == "2026-10-28"
    assert val(it, "k") == "01-Jan-2000 12:00:00"
    assert "char matrix" in error_of(it, "datestr([730486 730487])")


def test_datevec_clock_and_now(it):
    run(it, "v = datevec('2026-10-28 13:00:00'); w = datevec(730486.5); "
            "c = clock; n = now;")
    np.testing.assert_allclose(val(it, "v"), [2026, 10, 28, 13, 0, 0])
    np.testing.assert_allclose(val(it, "w"), [2000, 1, 1, 12, 0, 0])
    c = val(it, "c")
    assert c.shape == (6,) and c[0] == dt.date.today().year
    today = dt.date.today()
    assert math.floor(val(it, "n")) == matlab_datenum(today.year, today.month,
                                                      today.day) or \
        dt.date.today() != today


def test_datenum_refuses_what_it_cannot_read(it):
    assert "could not be read" in error_of(it, "datenum('not a date')")
    assert "fractional months" in error_of(it, "datenum(2000, 1.5, 1)")


# ──────────────────────────────────────────────────────────────
#  Bases
# ──────────────────────────────────────────────────────────────

def test_base_conversions(it):
    run(it, "a = dec2bin(10); b = dec2bin(5, 8); c = bin2dec('1010'); "
            "d = dec2hex(255); e = hex2dec('ff'); f = dec2base(35, 36); "
            "g = base2dec('Z', 36); h = bin2dec('1 0 1'); k = dec2bin(0); "
            "m = hex2dec({'A'; '10'});")
    assert (val(it, "a"), val(it, "b")) == ("1010", "00000101")
    assert (val(it, "c"), val(it, "d"), val(it, "e")) == (10, "FF", 255)
    assert (val(it, "f"), val(it, "g"), val(it, "h")) == ("Z", 35, 5)
    assert val(it, "k") == "0"
    np.testing.assert_array_equal(val(it, "m"), [[10], [16]])


def test_base_conversions_refuse(it):
    assert "char matrix" in error_of(it, "dec2bin([1 2])")
    assert "non-negative integer" in error_of(it, "dec2bin(-1)")
    assert "0 and 1" in error_of(it, "bin2dec('102')")
    assert "0-9, a-f" in error_of(it, "hex2dec('0xG')")


# ──────────────────────────────────────────────────────────────
#  Combinatorics and number theory
# ──────────────────────────────────────────────────────────────

def test_factorial_elementwise_and_overflow(it):
    """170! fits in a double; 171! is Inf."""
    run(it, "f = factorial([0 1 5; 10 170 171]);")
    f = val(it, "f")
    assert f.shape == (2, 3)
    np.testing.assert_array_equal(f[0], [1, 1, 120])
    assert f[1, 0] == math.factorial(10)
    assert f[1, 1] == pytest.approx(float(math.factorial(170)), rel=1e-14)
    assert f[1, 2] == math.inf
    assert "non-negative integers" in error_of(it, "factorial(2.5)")


def test_nchoosek_number_and_combinations(it):
    """C(5,2) = 10; combinations in lexicographic order of position."""
    run(it, "a = nchoosek(5, 2); b = nchoosek([10 20 30 40], 2); "
            "c = nchoosek(30, 15);")
    assert val(it, "a") == 10
    np.testing.assert_array_equal(val(it, "b"), [[10, 20], [10, 30],
                                                 [10, 40], [20, 30],
                                                 [20, 40], [30, 40]])
    assert val(it, "c") == math.comb(30, 15)
    assert "between 0 and N" in error_of(it, "nchoosek(3, 5)")


def test_primes_and_isprime_agree(it):
    """The sieve (primes) and Miller-Rabin (isprime) are independent."""
    run(it, "p = primes(30); q = find(isprime(1:30)); t = isprime(7); "
            "big = isprime(2^31 - 1); m = isprime([4; 5]);")
    np.testing.assert_array_equal(val(it, "p"),
                                  [2, 3, 5, 7, 11, 13, 17, 19, 23, 29])
    np.testing.assert_array_equal(val(it, "q"), val(it, "p"))
    assert val(it, "t") is True and val(it, "big") is True
    np.testing.assert_array_equal(val(it, "m"), [[False], [True]])
    assert "non-negative integers" in error_of(it, "isprime(-3)")


def test_gcd_lcm_and_bezout(it):
    """g = a*u + b*v; gcd(10,15) = 5 with u = -1, v = 1 (MATLAB's doc)."""
    run(it, "[g, u, v] = gcd(10, 15); h = gcd([12 18], 8); "
            "l = lcm([4 6], 10); z = gcd(0, 0);")
    assert (val(it, "g"), val(it, "u"), val(it, "v")) == (5, -1, 1)
    np.testing.assert_array_equal(val(it, "h"), [4, 2])
    np.testing.assert_array_equal(val(it, "l"), [20, 30])
    assert val(it, "z") == 0
    assert "real integers" in error_of(it, "gcd(1.5, 3)")


# ──────────────────────────────────────────────────────────────
#  Special functions
# ──────────────────────────────────────────────────────────────

def test_special_functions_keep_shapes(it):
    run(it, "a = erf([0.5; 1]); b = erfc(0.5); c = erfinv(0.5); "
            "d = gamma([5 0.5 0 -1]); e = gammaln(10); f = beta(2, 3); "
            "g = betaln(2, 3); h = nthroot(-27, 3); k = erfcinv(1);")
    a = val(it, "a")
    assert a.shape == (2, 1)
    np.testing.assert_allclose(a.ravel(), [math.erf(0.5), math.erf(1)])
    assert val(it, "b") == pytest.approx(math.erfc(0.5))
    assert math.erf(val(it, "c")) == pytest.approx(0.5)
    np.testing.assert_allclose(val(it, "d"), [24, math.sqrt(math.pi),
                                              math.inf, math.inf])
    assert val(it, "e") == pytest.approx(math.log(math.factorial(9)))
    assert val(it, "f") == pytest.approx(1 / 12)     # 1!2!/4!
    assert val(it, "g") == pytest.approx(math.log(1 / 12))
    assert val(it, "h") == -3
    assert val(it, "k") == 0


def test_special_functions_refuse(it):
    assert "real" in error_of(it, "erf(1i)")
    assert "nonnegative" in error_of(it, "gammaln(-1)")
    assert "odd integer" in error_of(it, "nthroot(-8, 2)")
