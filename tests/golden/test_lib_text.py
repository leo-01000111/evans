"""
Text functions: strsplit, regexp, contains, pad and the rest.

Each test types the command the way a user would at the MATLAB console and
checks it against a value worked out by hand: indices are counted on the
string, character by character, from 1.
"""

from __future__ import annotations

import numpy as np
import pytest

from evans.console import Interpreter, set_figure_sink
from evans.console.figures import recording_sink
from evans.console.matlab_runtime import Cell, Struct, StructArray


@pytest.fixture
def it():
    previous = set_figure_sink(recording_sink())
    yield Interpreter()
    set_figure_sink(previous)


def run(it, source: str):
    """Run MATLAB, insist it succeeded."""
    results = it.run_script(source, "matlab")
    failed = [r for r in results if r.error]
    assert not failed, f"{failed[0].source!r} → {failed[0].error}"


def error_of(it, source: str) -> str:
    """Run MATLAB that must fail; return the error text."""
    results = it.run_script(source, "matlab")
    failed = [r for r in results if r.error]
    assert failed, f"{source!r} ran without an error"
    return str(failed[0].error)


def val(it, name):
    return it.namespace[name]


def cell(it, name):
    """A cell's elements and its (rows, columns)."""
    c = val(it, name)
    assert isinstance(c, Cell)
    return list(c), c.dims


def row(it, name):
    a = np.asarray(val(it, name))
    return a.ravel().tolist(), a.ndim


# ──────────────────────────────────────────────────────────────
#  strsplit, strjoin, split, join
# ──────────────────────────────────────────────────────────────

def test_strsplit_default_whitespace_collapses(it):
    """
    ``'  a b\\t\\tc '``: the leading run, each inner run and the trailing
    space are one delimiter each, so the pieces are '', a, b, c, ''.
    """
    run(it, "c = strsplit(sprintf('  a b\\t\\tc '));")
    assert cell(it, "c") == (["", "a", "b", "c", ""], (1, 5))


def test_strsplit_delimiter_no_collapse_and_matches(it):
    """``'a,,b'`` at each comma: a, '', b; the delimiters found are two commas."""
    run(it, "[c, d] = strsplit('a,,b', ',', 'CollapseDelimiters', false);")
    assert cell(it, "c") == (["a", "", "b"], (1, 3))
    assert cell(it, "d") == ([",", ","], (1, 2))
    run(it, "c = strsplit('a,,b', ',');")
    assert cell(it, "c") == (["a", "b"], (1, 2))


def test_strsplit_cell_of_delimiters_and_escape(it):
    """``'a-b_c'`` at '-' or '_'; ``'\\t'`` in the delimiter is a tab."""
    run(it, "c = strsplit('a-b_c', {'-', '_'});")
    assert cell(it, "c") == (["a", "b", "c"], (1, 3))
    run(it, "c = strsplit(sprintf('x\\ty'), '\\t');")
    assert cell(it, "c") == (["x", "y"], (1, 2))


def test_strsplit_regular_expression(it):
    """Split at runs of digits: ``'ab12cd3e'`` → ab, cd, e."""
    run(it, "c = strsplit('ab12cd3e', '\\d+', "
            "'DelimiterType', 'RegularExpression');")
    assert cell(it, "c") == (["ab", "cd", "e"], (1, 3))


def test_strsplit_refuses_a_cell(it):
    assert "character vector" in error_of(it, "strsplit({'a b'})")


def test_strjoin(it):
    """Space by default; a given delimiter; one delimiter per gap."""
    run(it, "a = strjoin({'x','y','z'}); b = strjoin({'x','y'}, ', ');"
            "c = strjoin({'1','2','3'}, {'+','='});")
    assert val(it, "a") == "x y z"
    assert val(it, "b") == "x, y"
    assert val(it, "c") == "1+2=3"
    assert "1xN" in error_of(it, "strjoin({1, 2})")


def test_split_returns_a_column_cell(it):
    """MATLAB's string array becomes an N×1 cell of char."""
    run(it, "c = split('a b  c');")
    assert cell(it, "c") == (["a", "b", "c"], (3, 1))
    run(it, "c = split('1;2', ';');")
    assert cell(it, "c") == (["1", "2"], (2, 1))


def test_split_column_cell_gives_a_matrix(it):
    """Two strings of two pieces each: a 2×2 cell, one row per string."""
    run(it, "c = split({'a b'; 'c d'});")
    assert cell(it, "c") == (["a", "c", "b", "d"], (2, 2))


def test_join(it):
    """A row joins to char; a 2×2 cell joins each row into a column."""
    run(it, "a = join({'x','y'}); b = join({'x','y'}, '-');"
            "c = join({'a','b';'c','d'});")
    assert val(it, "a") == "x y"
    assert val(it, "b") == "x-y"
    assert cell(it, "c") == (["a b", "c d"], (2, 1))


# ──────────────────────────────────────────────────────────────
#  upper, lower, strtrim, strrep, deblank, blanks, pad
# ──────────────────────────────────────────────────────────────

def test_case_and_trim_on_char_and_cells(it):
    """The cell keeps its 2×1 shape."""
    run(it, "a = upper('aB1'); b = lower({'AB'; 'Cd'});"
            "c = strtrim(sprintf(' \\t x y \\n')); d = strtrim({' a', 'b '});")
    assert val(it, "a") == "AB1"
    assert cell(it, "b") == (["ab", "cd"], (2, 1))
    assert val(it, "c") == "x y"
    assert cell(it, "d") == (["a", "b"], (1, 2))


def test_strtrim_keeps_nonbreaking_space(it):
    """char(160) is "significant" whitespace to MATLAB's strtrim."""
    run(it, "c = strtrim([char(160) 'a ']);")
    assert val(it, "c") == "\xa0a"


def test_strtrim_refuses_a_number(it):
    assert "character array" in error_of(it, "strtrim(5)")


def test_strrep_replaces_overlapping_matches(it):
    """MATLAB's documented example: '22' in '222' is replaced twice."""
    run(it, "s = strrep('abc 2 def 22 ghi 222 jkl 2222', '22', '*');")
    assert val(it, "s") == "abc 2 def * ghi ** jkl ***"
    run(it, "c = strrep({'aXb', 'X'}, 'X', '--');")
    assert cell(it, "c") == (["a--b", "--"], (1, 2))


def test_deblank_and_blanks(it):
    run(it, "a = deblank(['ab  ' char(0)]); b = blanks(3);")
    assert val(it, "a") == "ab"
    assert val(it, "b") == "   "


def test_pad(it):
    """To the longest (3); to width 5 on both sides (extra on the right)."""
    run(it, "a = pad({'a', 'abc'}); b = pad('ab', 5, 'both', '*');"
            "c = pad('7', 3, 'left', '0'); d = pad('abcdef', 3);")
    assert cell(it, "a") == (["a  ", "abc"], (1, 2))
    assert val(it, "b") == "*ab**"
    assert val(it, "c") == "007"
    assert val(it, "d") == "abcdef"
    assert "Side" in error_of(it, "pad('a', 3, 'middle')")


# ──────────────────────────────────────────────────────────────
#  contains, startsWith, endsWith, strfind, strncmp
# ──────────────────────────────────────────────────────────────

def test_contains_on_a_cell_keeps_its_shape(it):
    """2×2 cell; 'ab' appears in abc and ab only."""
    run(it, "k = contains({'abc', 'xyz'; 'q', 'ab'}, 'ab');")
    assert np.asarray(val(it, "k")).tolist() == [[True, False],
                                                 [False, True]]


def test_contains_patterns_and_ignore_case(it):
    run(it, "a = contains('Hello', 'hell'); b = contains('Hello', 'hell', "
            "'IgnoreCase', true); c = contains('Hello', {'x', 'lo'});")
    assert val(it, "a") is False
    assert val(it, "b") is True
    assert val(it, "c") is True


def test_starts_and_ends_with(it):
    run(it, "a = startsWith({'data.csv', 'img.png'}, 'data');"
            "b = endsWith({'data.csv', 'img.PNG'}, {'.csv', '.png'}, "
            "'IgnoreCase', true);")
    assert np.asarray(val(it, "a")).tolist() == [True, False]
    assert np.asarray(val(it, "b")).tolist() == [True, True]
    assert "text" in error_of(it, "contains(5, 'a')")


def test_strfind(it):
    """'aa' in 'aaa' starts at 1 and 2 (overlapping); none in 'b'."""
    run(it, "k = strfind('aaa', 'aa'); e = strfind('b', 'a');"
            "c = strfind({'abab', 'x'}, 'b');")
    assert row(it, "k") == ([1, 2], 1)
    assert np.asarray(val(it, "e")).size == 0
    items, dims = cell(it, "c")
    assert dims == (1, 2)
    assert np.asarray(items[0]).tolist() == [2, 4]
    assert np.asarray(items[1]).size == 0


def test_strncmp(it):
    run(it, "a = strncmp('abcd', 'abxx', 2); b = strncmp('abcd', 'abxx', 3);"
            "c = strncmpi('ABc', 'abd', 2); d = strncmp({'ab1', 'xy'}, 'ab', 2);")
    assert val(it, "a") is True
    assert val(it, "b") is False
    assert val(it, "c") is True
    assert np.asarray(val(it, "d")).tolist() == [True, False]


def test_character_classes(it):
    """'a 1!': letter, space, digit, punctuation."""
    run(it, "s = isspace('a 1!'); l = isletter('a 1!');"
            "d = isstrprop('a 1!', 'digit'); p = isstrprop('a 1!', 'punct');")
    assert row(it, "s")[0] == [False, True, False, False]
    assert row(it, "l")[0] == [True, False, False, False]
    assert row(it, "d")[0] == [False, False, True, False]
    assert row(it, "p")[0] == [False, False, False, True]
    assert "category" in error_of(it, "isstrprop('a', 'vowel')")


# ──────────────────────────────────────────────────────────────
#  regexp, regexpi, regexprep
# ──────────────────────────────────────────────────────────────

def test_regexp_default_output_order(it):
    """
    ``'ab12cd345'``, pattern two digits: '12' at 3–4, '34' at 7–8 (counted
    a=1 b=2 1=3 2=4 c=5 d=6 3=7 4=8 5=9). Tokens '1','2' and '3','4';
    split pieces 'ab', 'cd', '5'.
    """
    run(it, "[s, e, te, m, t, nm, sp] = regexp('ab12cd345', '(\\d)(\\d)');")
    assert row(it, "s") == ([3, 7], 1)
    assert row(it, "e") == ([4, 8], 1)
    te, dims = cell(it, "te")
    assert dims == (1, 2)
    assert np.asarray(te[0]).tolist() == [[3, 3], [4, 4]]
    assert cell(it, "m") == (["12", "34"], (1, 2))
    tokens, dims = cell(it, "t")
    assert dims == (1, 2)
    assert [list(k) for k in tokens] == [["1", "2"], ["3", "4"]]
    assert all(k.dims == (1, 2) for k in tokens)
    assert cell(it, "sp") == (["ab", "cd", "5"], (1, 3))


def test_regexp_keyword_order(it):
    """Outputs come in the order the keywords are given."""
    run(it, "[t, m] = regexp('x=1, y=22', '(\\w)=(\\d+)', 'tokens', 'match');")
    assert cell(it, "m") == (["x=1", "y=22"], (1, 2))
    assert [list(k) for k in val(it, "t")] == [["x", "1"], ["y", "22"]]
    run(it, "e = regexp('x=1, y=22', '\\d+', 'end');")
    assert row(it, "e") == ([3, 9], 1)


def test_regexp_tokens_without_groups_is_the_match(it):
    run(it, "t = regexp('a1b2', '\\d', 'tokens');")
    assert [list(k) for k in val(it, "t")] == [["1"], ["2"]]


def test_regexp_names(it):
    """Two matches: a 1×2 struct array; one match: a struct."""
    run(it, "n = regexp('x=1, y=22', '(?<key>\\w)=(?<value>\\d+)', 'names');")
    n = val(it, "n")
    assert isinstance(n, StructArray) and len(n) == 2
    assert dict(n[1]) == {"key": "y", "value": "22"}
    run(it, "n = regexp('v=7', '(?<key>\\w)=(?<value>\\d+)', 'names');"
            "k = n.key;")
    assert isinstance(val(it, "n"), Struct)
    assert val(it, "k") == "v"


def test_regexp_once(it):
    run(it, "m = regexp('ab12c3', '\\d+', 'match', 'once');"
            "s = regexp('ab12c3', '\\d+', 'once');"
            "t = regexp('ab12c3', '(\\w)(\\d)', 'tokens', 'once');"
            "z = regexp('abc', '\\d', 'match', 'once');")
    assert val(it, "m") == "12"
    assert val(it, "s") == 3
    assert cell(it, "t") == (["b", "1"], (1, 2))
    assert val(it, "z") == ""


def test_regexp_on_a_cell(it):
    """Each output is a cell of per-string results, the input's shape."""
    run(it, "m = regexp({'a1'; 'b22c3'}, '\\d+', 'match');"
            "s = regexp({'a1'; 'b22c3'}, '\\d+');")
    items, dims = cell(it, "m")
    assert dims == (2, 1)
    assert [list(x) for x in items] == [["1"], ["22", "3"]]
    starts, _ = cell(it, "s")
    assert [np.atleast_1d(x).tolist() for x in starts] == [[2], [2, 5]]


def test_regexp_word_boundaries_and_case(it):
    """``\\<\\w`` is the first letter of each word."""
    run(it, "w = regexp('the cat', '\\<\\w', 'match');"
            "i = regexpi('ABC abc', 'b', 'start');"
            "j = regexp('ABC abc', 'b', 'start', 'ignorecase');")
    assert cell(it, "w") == (["t", "c"], (1, 2))
    assert row(it, "i") == ([2, 6], 1)
    assert row(it, "j") == ([2, 6], 1)


def test_regexp_ignores_empty_matches_by_default(it):
    """``a*`` on 'baa' matches 'aa' only; with 'emptymatch' also '' at 1 and 4."""
    run(it, "m = regexp('baa', 'a*', 'match');"
            "s = regexp('baa', 'a*', 'start', 'emptymatch');")
    assert cell(it, "m") == (["aa"], (1, 1))
    assert row(it, "s")[0] == [1, 2, 4]


def test_regexp_refuses_bad_options(it):
    assert "not an option" in error_of(it, "regexp('a', 'a', 'bogus')")
    assert "Invalid regular expression" in error_of(it, "regexp('a', '(')")


def test_regexprep(it):
    run(it, "a = regexprep('hello world', '(\\w+) (\\w+)', '$2 $1');"
            "b = regexprep('aaa', 'a', 'b', 'once');"
            "c = regexprep('Abc', 'a', 'x', 'ignorecase');"
            "d = regexprep({'a1', 'b2'}, '\\d', '#');"
            "e = regexprep('k=v', '(?<l>\\w)=(?<r>\\w)', '$<r>=$<l>');"
            "f = regexprep('aaa', 'a', 'b', 2);"
            "g = regexprep('x', 'x', 'a\\nb');")
    assert val(it, "a") == "world hello"
    assert val(it, "b") == "baa"
    assert val(it, "c") == "xbc"
    assert cell(it, "d") == (["a#", "b#"], (1, 2))
    assert val(it, "e") == "v=k"
    assert val(it, "f") == "aba"
    assert val(it, "g") == "a\nb"
    assert "preservecase" in error_of(
        it, "regexprep('a', 'a', 'b', 'preservecase')")


# ──────────────────────────────────────────────────────────────
#  sprintf and num2str over cells
# ──────────────────────────────────────────────────────────────

def test_sprintf_comma_list_from_a_cell(it):
    """``c{:}`` hands each element to sprintf, so the format recycles."""
    run(it, "c = {'a', 'bb'}; s = sprintf('%s,', c{:});")
    assert val(it, "s") == "a,bb,"


def test_sprintf_refuses_a_cell(it):
    """MATLAB: "Function is not defined for 'cell' inputs." """
    assert "'cell' inputs" in error_of(it, "sprintf('%s', {'a'})")


def test_num2str_refuses_a_cell(it):
    """MATLAB: "Input to num2str must be numeric." """
    assert "must be numeric" in error_of(it, "num2str({1})")
