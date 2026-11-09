"""
Integer and single types, and string arrays: the Phase 4 type system.

Expected values are MATLAB's, from its documentation of integer arithmetic
(round half away from zero, saturate, an integer meets a double) and of
string arrays.
"""

import numpy as np
import pytest

from evans.console import set_figure_sink
from evans.console.figures import recording_sink
from evans.console.interpreter import Interpreter


@pytest.fixture
def it():
    return Interpreter()


@pytest.fixture
def sink():
    recorder = recording_sink()
    previous = set_figure_sink(recorder)
    yield recorder
    set_figure_sink(previous)


def last(sink):
    return sink.figures[-1]


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


def cls(it, expr) -> str:
    return value(it, f"class({expr})")


# ── construction, saturation, rounding ─────────────────────────

@pytest.mark.parametrize("name, low, high", [
    ("int8", -128, 127), ("int16", -32768, 32767),
    ("int32", -2**31, 2**31 - 1), ("int64", -2**63, 2**63 - 1),
    ("uint8", 0, 255), ("uint16", 0, 65535), ("uint32", 0, 2**32 - 1),
    ("uint64", 0, 2**64 - 1)])
def test_each_integer_class_saturates_at_its_limits(it, name, low, high):
    assert int(value(it, f"{name}(1e30)")) == high
    assert int(value(it, f"{name}(-1e30)")) == low
    assert cls(it, f"{name}(5)") == name
    assert int(value(it, f"intmax('{name}')")) == high
    assert int(value(it, f"intmin('{name}')")) == low


def test_conversion_rounds_halves_away_from_zero(it):
    assert [int(value(it, e)) for e in
            ("int8(2.5)", "int8(-2.5)", "int8(3.5)", "uint8(0.5)",
             "int8(-0.4)")] == [3, -3, 4, 1, 0]


def test_nan_becomes_zero(it):
    assert int(value(it, "int16(NaN)")) == 0


def test_an_integer_array_converts_elementwise(it):
    a = value(it, "uint8([10.4 255.6 -3])")
    assert a.dtype == np.uint8 and a.tolist() == [10, 255, 0]


def test_logical_double_and_cast(it):
    assert cls(it, "logical([1 0 2])") == "logical"
    assert value(it, "logical([1 0 2])").tolist() == [True, False, True]
    assert "NaN" in error(it, "logical(NaN)")
    assert cls(it, "double(int8(5))") == "double"
    assert value(it, "double(int8(5)) / 2") == 2.5
    assert cls(it, "cast(7, 'uint16')") == "uint16"
    assert int(value(it, "cast(300, 'uint8')")) == 255
    assert value(it, "double('AB')").tolist() == [65, 66]


# ── arithmetic ─────────────────────────────────────────────────

def test_integer_arithmetic_saturates(it):
    assert int(value(it, "int8(100) + int8(100)")) == 127
    assert int(value(it, "uint8(5) - 10")) == 0
    assert int(value(it, "int8(-100) - int8(100)")) == -128
    assert int(value(it, "uint8(200) * 2")) == 255
    assert int(value(it, "int8(2)^7")) == 127
    assert int(value(it, "-int8(-128)")) == 127


def test_integer_division_rounds_to_nearest(it):
    assert int(value(it, "int32(7) / int32(2)")) == 4
    assert int(value(it, "int32(-7) / int32(2)")) == -4
    assert int(value(it, "5 / int8(2)")) == 3
    assert int(value(it, "int8(5) / 0")) == 127
    assert int(value(it, "int8(-5) / 0")) == -128
    assert int(value(it, "int8(0) / 0")) == 0
    assert int(value(it, "idivide(int32(7), int32(2))")) == 3
    assert int(value(it, "idivide(int32(7), int32(2), 'floor')")) == 3
    assert int(value(it, "idivide(int32(7), int32(2), 'ceil')")) == 4


def test_an_integer_meets_a_double_and_keeps_its_class(it):
    assert cls(it, "int8([1 2 3]) * 2.6") == "int8"
    assert value(it, "int8([1 2 3]) * 2.6").tolist() == [3, 5, 8]
    assert cls(it, "2.6 + uint8(1)") == "uint8"
    assert cls(it, "int16(1) + true") == "int16"


def test_two_different_integer_classes_do_not_mix(it):
    message = error(it, "int8(1) + int16(1)")
    assert "Integers can only be combined" in message
    assert "int8" in message and "int16" in message
    assert "Integers can only be combined" in error(it, "uint8(1) .* int8(1)")


def test_comparisons_give_logicals(it):
    assert value(it, "int8(5) == 5") is True or value(it, "int8(5) == 5") == 1
    assert cls(it, "int8(5) == 5") == "logical"
    assert value(it, "uint8([1 2 3]) > 1").tolist() == [False, True, True]
    assert value(it, "uint8(200) > 300") == 0


def test_single_arithmetic(it):
    assert cls(it, "single(1) + 1") == "single"
    assert cls(it, "single(1) + single(2)") == "single"
    assert cls(it, "single(2) * int8(3)") == "int8"
    assert float(value(it, "single(0.1) + single(0.2)")) == pytest.approx(
        0.3, abs=1e-7)
    assert float(value(it, "single(1) / 3")) != 1 / 3         # rounded to 24 bits
    assert float(value(it, "single(1) / 3")) == pytest.approx(1 / 3,
                                                              rel=1e-6)


def test_class_of_everything_that_is_not_an_integer_stays_double(it):
    for expr in ("1:3", "find([0 1 1])", "numel([1 2])", "size(ones(2,3))",
                 "length('abc')", "sum([1 2])", "mean(int8([1 2 4]))",
                 "double(int8(3))", "randi(5)", "round(2.5)", "zeros(2)",
                 "[1 2 3] + 1", "true + true"):
        assert cls(it, expr) == "double", expr
    assert cls(it, "[1 2] > 1") == "logical"


# ── library functions on typed values ──────────────────────────

def test_functions_keep_the_class_of_their_input(it):
    assert cls(it, "sum(int8([100 100]))") == "int8"
    assert int(value(it, "sum(int8([100 100]))")) == 127
    assert int(value(it, "abs(int8(-128))")) == 127
    assert cls(it, "max(uint8([3 9 2]))") == "uint8"
    assert cls(it, "sort(int16([3 1 2]))") == "int16"
    assert value(it, "sort(int16([3 1 2]))").tolist() == [1, 2, 3]
    assert cls(it, "reshape(int8(1:6), 2, 3)") == "int8"
    assert cls(it, "cumsum(uint8([200 100]))") == "uint8"
    assert value(it, "cumsum(uint8([200 100]))").tolist() == [200, 255]
    assert cls(it, "mod(int8(10), 3)") == "int8"
    assert int(value(it, "mod(int8(10), 3)")) == 1
    assert cls(it, "floor(int8(3))") == "int8"


def test_find_and_friends_return_doubles_even_for_integer_input(it):
    assert cls(it, "find(uint8([0 1 1]))") == "double"
    assert cls(it, "numel(uint8([0 1 1]))") == "double"
    run(it, "[m, k] = max(int8([3 9 2]))")
    assert cls(it, "m") == "int8" and cls(it, "k") == "double"
    assert value(it, "k") == 2


def test_zeros_and_ones_take_a_class(it):
    a = value(it, "zeros(2, 3, 'int8')")
    assert a.dtype == np.int8 and a.shape == (2, 3)
    assert cls(it, "ones(1, 4, 'uint16')") == "uint16"
    assert cls(it, "zeros(2, 'single')") == "single"
    assert cls(it, "zeros(2, 'like', int8(1))") == "int8"
    assert cls(it, "zeros(1, 3, 'double')") == "double"
    assert cls(it, "zeros(3)") == "double"
    assert "Invalid data type" in error(it, "zeros(3, 'banana')")


def test_class_predicates(it):
    assert value(it, "isinteger(int8(3))") and not value(it, "isinteger(3)")
    assert value(it, "isfloat(single(3))") and value(it, "isfloat(3)")
    assert not value(it, "isfloat(int8(3))")
    assert value(it, "isnumeric(int8(3))") and value(it, "isnumeric(single(1))")
    assert not value(it, "isnumeric(true)")
    assert value(it, "isa(int8(1), 'integer')")
    assert value(it, "isa(int8(1), 'numeric')")
    assert value(it, "isa(single(1), 'float')")
    assert not value(it, "isa(int8(1), 'float')")
    assert value(it, "isa(uint8(1), 'uint8')")


def test_limits(it):
    assert int(value(it, "intmax")) == 2**31 - 1
    assert cls(it, "intmax") == "int32"
    assert int(value(it, "intmax('int8') + 1")) == 127
    assert int(value(it, "intmin(int16(4))")) == -32768
    assert value(it, "flintmax") == 2.0**53
    assert float(value(it, "flintmax('single')")) == 2.0**24
    assert value(it, "realmax") == np.finfo(float).max
    assert cls(it, "realmax('single')") == "single"
    assert float(value(it, "realmin('single')")) == pytest.approx(
        np.finfo(np.float32).tiny)


def test_bit_functions(it):
    assert value(it, "bitand(12, 10)") == 8
    assert value(it, "bitor(12, 10)") == 14
    assert value(it, "bitxor(12, 10)") == 6
    assert cls(it, "bitand(12, 10)") == "double"
    assert cls(it, "bitand(uint8(255), uint8(15))") == "uint8"
    assert int(value(it, "bitshift(uint8(255), 1)")) == 254
    assert value(it, "bitshift(16, -2)") == 4
    assert value(it, "bitshift(1, 4)") == 16
    assert int(value(it, "bitcmp(uint8(5))")) == 250


# ── indexing, assignment, concatenation ────────────────────────

def test_indexing_keeps_the_class(it):
    run(it, "x = uint8([10 20 30; 40 50 60]);")
    assert cls(it, "x(1, 2)") == "uint8"
    assert cls(it, "x(:, 1)") == "uint8"
    assert cls(it, "x(end)") == "uint8"
    assert int(value(it, "x(2, 3)")) == 60


def test_assigning_into_an_integer_array_saturates(it):
    run(it, "x = uint8([10 20 30]); x(2) = 300; x(3) = -5; x(1) = 7.6;")
    assert value(it, "x").tolist() == [8, 255, 0]
    assert cls(it, "x") == "uint8"


def test_growing_an_integer_array_keeps_its_class(it):
    run(it, "x = int8([]); x(3) = 9;")
    assert cls(it, "x") == "int8"
    assert value(it, "x").tolist() == [0, 0, 9]


def test_assigning_an_integer_into_a_double_array_converts_it(it):
    run(it, "y = [1.5 2.5 3.5]; y(2) = int8(7);")
    assert cls(it, "y") == "int8"
    assert value(it, "y").tolist() == [2, 7, 4]


def test_concatenation_takes_the_first_integer_class(it):
    assert cls(it, "[int8(1) 2.7 300]") == "int8"
    assert value(it, "[int8(1) 2.7 300]").tolist() == [1, 3, 127]
    assert cls(it, "[1 uint8(2)]") == "uint8"
    assert cls(it, "[single(1) 2]") == "single"
    assert cls(it, "[int8(1); 2]") == "int8"
    assert cls(it, "[uint8(200) int16(1000)]") == "uint8"


def test_colon_with_integers(it):
    assert cls(it, "uint8(250):uint8(255)") == "uint8"
    assert value(it, "uint8(250):uint8(255)").tolist() == list(range(250, 256))


def test_for_loop_over_an_integer_array(it):
    run(it, "t = 0; for k = uint8([100 100 100]), t = t + k; end")
    assert int(value(it, "t")) == 255
    assert cls(it, "t") == "uint8"


def test_a_function_gets_and_returns_integers(it):
    run(it, "f = @(a) a * 2;")
    assert int(value(it, "f(int8(100))")) == 127
    assert cls(it, "f(int8(100))") == "int8"


# ── display ────────────────────────────────────────────────────

def test_integer_display(it):
    out = run(it, "a = int8(5)").output + run(
        it, "b = int16([100 -200; 3 4])").output
    assert "a = 5" in out
    assert "100  -200" in out and "-200" in out
    assert "." not in out                                # no decimals


def test_a_large_integer_is_not_written_in_exponent_form(it):
    assert "9223372036854775807" in run(it, "n = intmax('int64')").output


def test_single_display(it):
    assert "x = 3.1416" in run(it, "x = single(pi)").output


# ── string arrays ──────────────────────────────────────────────

def test_a_double_quoted_literal_is_a_string_scalar(it):
    assert cls(it, '"abc"') == "string"
    assert cls(it, "'abc'") == "char"
    assert value(it, 'numel("hello")') == 1
    assert value(it, "numel('hello')") == 5
    assert value(it, 'length("hello")') == 1
    assert value(it, 'size("abc")').tolist() == [1, 1]
    assert value(it, 'strlength("hello")') == 5
    assert value(it, "strlength('hello')") == 5


def test_string_array_concatenation(it):
    run(it, 't = ["a" "bc" "def"];')
    assert cls(it, "t") == "string"
    assert value(it, "numel(t)") == 3
    assert value(it, "strlength(t)").tolist() == [1, 2, 3]
    assert cls(it, "t(2)") == "string"
    assert value(it, "t(2)") == "bc"
    assert value(it, "t(end)") == "def"
    assert value(it, 'numel(["a"; "b"])') == 2
    assert value(it, 'size(["a"; "b"])').tolist() == [2, 1]
    assert value(it, "numel([\"ab\" 'cd'])") == 2
    assert error(it, '["a" "b"; "c"]')


def test_char_concatenation_is_unchanged(it):
    assert value(it, "['ab' 'cd']") == "abcd"
    assert cls(it, "['ab' 'cd']") == "char"
    assert value(it, "['ab'; 'cd']") is not None


def test_plus_joins_strings(it):
    assert value(it, '"foo" + "bar"') == "foobar"
    assert cls(it, '"foo" + "bar"') == "string"
    assert value(it, '"n = " + 5') == "n = 5"
    assert list(value(it, '"a" + ["x" "y"]')) == ["ax", "ay"]
    assert "not supported" in error(it, '"a" - "b"')
    assert "not supported" in error(it, '"a" * 2')


def test_string_comparison(it):
    assert value(it, '"abc" == "abc"')
    assert not value(it, '"abc" == "abd"')
    assert value(it, "\"abc\" == 'abc'")
    assert value(it, '"abc" ~= "abd"')
    assert value(it, '"apple" < "banana"')
    assert value(it, '["a" "b" "a"] == "a"').tolist() == [True, False, True]
    assert value(it, '["a" "b"] == ["a" "c"]').tolist() == [True, False]
    assert value(it, 'strcmp("abc", "abc")')
    assert value(it, "strcmp('abc', \"abc\")")


def test_the_string_function(it):
    assert cls(it, "string('hello')") == "string"
    assert value(it, "string(42)") == "42"
    assert value(it, "string(3.5)") == "3.5"
    assert list(value(it, "string([1 2 3])")) == ["1", "2", "3"]
    assert list(value(it, "string({'a', 'bc'})")) == ["a", "bc"]
    assert cls(it, "char(\"abc\")") == "char"
    assert value(it, "isstring(\"a\")") and not value(it, "isstring('a')")
    assert value(it, "ischar('a')") and not value(it, 'ischar("a")')


def test_text_functions_give_strings_back_for_strings(it):
    assert cls(it, 'upper("abc")') == "string"
    assert value(it, 'upper("abc")') == "ABC"
    assert cls(it, "upper('abc')") == "char"
    assert cls(it, 'strtrim("  a ")') == "string"
    assert cls(it, 'strrep("abc", "b", "x")') == "string"
    assert value(it, 'strrep("abc", "b", "x")') == "axc"
    assert value(it, 'join(["a" "b"], "-")') == "a-b"
    assert value(it, 'contains("hello", "ell")')
    assert value(it, 'startsWith("hello", "he")')


def test_strings_work_where_char_did(it):
    run(it, 's = struct("name", "Ada", "n", 3);')
    assert value(it, "s.name") == "Ada"
    assert cls(it, "s.name") == "string"
    run(it, 'fprintf("%s has %d\\n", s.name, s.n)')
    assert value(it, 'sprintf("%d-%s", 5, "x")') == "5-x"
    run(it, 'switch "b", case "a", r = 1; case "b", r = 2; end')
    assert value(it, "r") == 2
    run(it, 'm = containers.Map(); m("k") = 4;')
    assert value(it, 'm("k")') == 4
    run(it, 'c = {"a", "b"};')
    assert value(it, "c{2}") == "b"
    assert not value(it, 'iscell(["a" "b"])')
    assert value(it, "iscell(c)")


def test_a_string_index_beyond_its_length_errors(it):
    assert error(it, 's = "abc"; s(2)')


def test_string_display(it):
    out = run(it, 's = "abc"').output + run(it, 't = ["a" "bc"]').output
    assert '"abc"' in out
    assert "1×2 string array" in out and '"a"' in out and '"bc"' in out


def test_func2str_keeps_the_quotes_it_was_written_with(it):
    assert value(it, "func2str(@() \"a\")") == '@()"a"'
    assert value(it, "func2str(@() 'a')") == "@()'a'"


# ── images ─────────────────────────────────────────────────────

def test_imshow_of_a_uint8_image_spans_0_to_255(it, sink):
    run(it, "imshow(uint8([0 128; 255 64]))")
    spec = last(sink)
    assert spec.extra["clim"] == (0.0, 255.0)
    run(it, "imshow(uint16([0 1000]))")
    assert last(sink).extra["clim"] == (0.0, 65535.0)
    run(it, "imshow(single([0 0.5]))")
    assert last(sink).extra["clim"] == (0.0, 1.0)
