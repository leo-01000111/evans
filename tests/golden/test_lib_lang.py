"""
The language functions: ``eval`` and friends, ``containers.Map``, ``magic``,
``fileread``, and the "not in Evans" error.
"""

import numpy as np
import pytest

from evans import help as pages
from evans.console import matlab_names
from evans.console.interpreter import Interpreter


@pytest.fixture
def it():
    return Interpreter()


def run(it, source):
    result = it.command(source)
    assert result.ok, f"{source}\n→ {result.error}"
    return result


def value(it, expr):
    return it.evaluate(expr)


def error(it, source) -> str:
    result = it.command(source)
    assert not result.ok, f"{source} should have failed"
    return result.error


# ── the "not in Evans" error ───────────────────────────────────

def test_a_missing_matlab_function_says_it_is_not_a_typo(it):
    message = error(it, "accumarray(1, 2)")
    assert "Unrecognized function or variable 'accumarray'" in message
    assert "not a typo" in message


def test_a_typo_gets_the_plain_error(it):
    message = error(it, "zeroz(3)")
    assert "Unrecognized function or variable 'zeroz'" in message
    assert "not a typo" not in message


def test_no_listed_name_is_implemented(it):
    runtime = it._matlab_runtime()
    have = set(runtime.lib.names) | set(it.namespace)
    assert sorted(matlab_names.ALL & have) == []


def test_the_not_in_evans_page_lists_every_name():
    text = pages.load("not_in_evans")
    flat = " ".join(str(b) for _, blocks in text.sections for b in blocks)
    for name in matlab_names.ALL:
        assert f"`{name}`" in flat or name in flat, name


# ── magic and fileread ─────────────────────────────────────────

@pytest.mark.parametrize("n", [3, 4, 5, 6, 8, 10])
def test_magic_squares_are_magic(it, n):
    m = np.asarray(value(it, f"magic({n})"), dtype=float)
    total = n * (n * n + 1) / 2
    assert sorted(m.reshape(-1)) == list(range(1, n * n + 1))
    assert np.all(m.sum(axis=0) == total) and np.all(m.sum(axis=1) == total)
    assert np.trace(m) == total and np.trace(np.fliplr(m)) == total


def test_magic_matches_matlab_exactly(it):
    assert np.array_equal(value(it, "magic(3)"),
                          [[8, 1, 6], [3, 5, 7], [4, 9, 2]])
    assert np.array_equal(value(it, "magic(4)"),
                          [[16, 2, 3, 13], [5, 11, 10, 8],
                           [9, 7, 6, 12], [4, 14, 15, 1]])
    assert np.array_equal(value(it, "magic(6)")[0], [35, 1, 6, 26, 19, 24])


def test_fileread_returns_the_text(it, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_bytes(b"hello\nworld")
    assert value(it, "fileread('a.txt')") == "hello\nworld"
    assert "Unable to open file" in error(it, "fileread('nope.txt')")


# ── function handles as text ───────────────────────────────────

def test_func2str_gives_the_handle_as_written(it):
    run(it, "f = @(x, y) x.^2 + y;")
    assert value(it, "func2str(f)") == "@(x,y)x.^2+y"
    assert value(it, "func2str(@sin)") == "sin"


def test_a_handle_in_a_variable_can_be_passed_as_an_argument(it):
    # A bare name used to call the function it held, with no inputs.
    run(it, "h = @(x, y) x + y;")
    assert value(it, "cellfun(h, {1, 2}, {10, 20})") is not None
    assert list(value(it, "cellfun(h, {1, 2}, {10, 20})")) == [11, 22]


def test_str2func_and_feval(it):
    run(it, "g = str2func('@(t) t*2');")
    assert value(it, "g(4)") == 8
    assert value(it, "feval('max', [3 9 2])") == 9
    assert value(it, "feval(@plus, 1, 2)") == 3
    run(it, "[m, i] = feval(@max, [3 9 2]);")
    assert (value(it, "m"), value(it, "i")) == (9, 2)


def test_nargin_of_a_function(it):
    run(it, "f = @(a, b, c) a + b + c;")
    assert value(it, "nargin(f)") == 3
    run(it, "v = @(a, varargin) a;")
    assert value(it, "nargin(v)") == -2


# ── eval ───────────────────────────────────────────────────────

def test_eval_runs_in_the_workspace_and_echoes(it):
    result = run(it, "eval('q = 7')")
    assert "q = 7" in result.output
    assert value(it, "q") == 7


def test_eval_with_an_output_returns_the_value(it):
    assert value(it, "eval('3*3')") == 9
    run(it, "z = eval('3*3');")
    assert value(it, "z") == 9


def test_eval_runs_the_catch_text_on_an_error(it):
    run(it, "eval('1 +* 2', 'w = 5;');")
    assert value(it, "w") == 5
    run(it, "eval('nosuchthing + 1', 'w = 6;');")
    assert value(it, "w") == 6


def test_eval_without_a_catch_reports_the_error(it):
    assert "Unrecognized function or variable" in error(it, "eval('nosuch')")


def test_evalin_base(it):
    run(it, "k = 4;")
    assert value(it, "evalin('base', 'k + 1')") == 5
    assert "base" in error(it, "evalin('caller', 'k')")


def test_eval_in_a_function_reads_but_never_silently_loses_a_write(
        it, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "reads.m").write_text(
        "function y = reads(a)\ny = eval('a + 1');\nend\n")
    (tmp_path / "writes.m").write_text(
        "function y = writes(a)\neval('b = a + 1;');\ny = a;\nend\n")
    assert value(it, "reads(2)") == 3
    assert "eval inside a function" in error(it, "writes(2)")


# ── validateattributes ─────────────────────────────────────────

def test_validateattributes_passes_and_fails(it):
    run(it, "validateattributes(5, {'numeric'}, {'positive', 'scalar'})")
    run(it, "validateattributes([1 2 3], {'numeric'}, {'vector', '>=', 1})")
    assert "to be positive" in error(
        it, "validateattributes(-5, {'numeric'}, {'positive'})")
    assert "scalar" in error(
        it, "validateattributes([1 2], {'numeric'}, {'scalar'})")
    assert "one of these types" in error(
        it, "validateattributes('a', {'numeric'}, {})")
    assert "x to be" in error(
        it, "validateattributes(-1, {'numeric'}, {'positive'}, 'f', 'x')")


# ── containers.Map ─────────────────────────────────────────────

def test_a_map_stores_and_reads_values(it):
    run(it, "m = containers.Map(); m('a') = 1; m('b') = [1 2 3];")
    assert value(it, "m.Count") == 2
    assert list(value(it, "m('b')")) == [1, 2, 3]
    assert value(it, "isKey(m, 'a')") is True
    assert list(value(it, "isKey(m, {'a', 'z'})")) == [True, False]
    assert list(value(it, "keys(m)")) == ["a", "b"]
    assert value(it, "class(m)") == "containers.Map"
    assert value(it, "length(m)") == 2


def test_a_map_is_a_handle(it):
    run(it, "m = containers.Map(); n = m; n('c') = 5;")
    assert value(it, "m.Count") == 1
    assert value(it, "m('c')") == 5


def test_a_map_from_keys_and_values(it):
    run(it, "m = containers.Map({'x', 'y'}, [10 20]);")
    assert value(it, "m('y')") == 20
    assert value(it, "m.ValueType") == "double"
    run(it, "s = containers.Map('one', 1);")
    assert value(it, "s('one')") == 1
    assert list(value(it, "values(m, {'y', 'x'})")) == [20, 10]


def test_a_numeric_map_sorts_its_keys_as_numbers(it):
    run(it, "m = containers.Map('KeyType', 'double', 'ValueType', 'any');"
            "m(10) = 'a'; m(2) = 'b';")
    assert list(value(it, "keys(m)")) == [2, 10]


def test_removing_and_missing_keys(it):
    run(it, "m = containers.Map({'a', 'b'}, [1 2]); remove(m, 'a');")
    assert value(it, "m.Count") == 1
    assert "not present" in error(it, "m('a')")
    assert "not present" in error(it, "remove(m, 'a')")
    assert "key type" in error(it, "m(3)")


def test_a_map_method_syntax(it):
    run(it, "m = containers.Map({'b', 'a'}, [2 1]);")
    assert list(value(it, "m.keys()")) == ["a", "b"]
    assert list(value(it, "m.values()")) == [1, 2]
    assert value(it, "m.isKey('a')") is True


def test_a_variable_called_containers_is_left_alone(it):
    run(it, "containers = struct('Map', 3);")
    assert value(it, "containers.Map") == 3
