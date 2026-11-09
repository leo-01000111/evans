"""
Phase 4 language core: arity errors, errors that name the function and line,
dotted script names, ``inputParser`` and nested functions.
"""

import pytest

from evans.console.interpreter import Interpreter


@pytest.fixture
def it():
    return Interpreter()


def run_script(it, source, folder=None):
    results = it.run_matlab(source, folder)
    errors = [r for r in results if r.error]
    out = "".join(r.output for r in results)
    return (errors[0].error if errors else None), out


F2 = "function y = f(a, b)\n  y = a + b;\nend\n"


# ── arity ──────────────────────────────────────────────────────

def test_too_many_inputs_to_a_function(it):
    error, _ = run_script(it, F2 + "f(1, 2, 3)")
    assert "Too many input arguments." in error
    assert "TypeError" not in error


def test_a_missing_parameter_that_is_used_is_named(it):
    error, _ = run_script(it, F2 + "f(1)")
    assert "Unrecognized function or variable 'b'." in error
    assert "NoneType" not in error


def test_a_missing_parameter_that_is_not_used_is_fine(it):
    _, out = run_script(it, "function y = g(a, b)\n  y = a;\nend\n"
                            "disp(g(4))")
    assert out.strip() == "4"


def test_nargin_and_exist_still_see_missing_arguments(it):
    src = ("function y = h(a, b)\n"
           "  if nargin < 2, b = 10; end\n"
           "  y = [nargin, exist('b', 'var'), exist('a', 'var')];\n"
           "  y = [y, b];\nend\n"
           "disp(h(1))\ndisp(h(1, 2))")
    error, out = run_script(it, src)
    assert error is None
    lines = out.split("\n")
    assert [float(x) for x in lines[0].split()] == [1, 1, 1, 10]
    assert [float(x) for x in lines[1].split()] == [2, 1, 1, 2]


def test_varargin_functions_take_any_number(it):
    _, out = run_script(it, "function n = cnt(varargin)\n  n = nargin;\nend\n"
                            "disp(cnt(1, 2, 3, 4))")
    assert out.strip() == "4"


def test_anonymous_function_arity(it):
    error, _ = run_script(it, "g = @(x) x + 1;\ng(1, 2)")
    assert error.endswith("Too many input arguments.")
    error, _ = run_script(it, "g = @(x) x + 1;\ng()")
    assert error.endswith("Not enough input arguments.")


def test_arity_errors_can_be_caught_with_matlab_messages(it):
    src = ("g = @(x) x;\n"
           "try, g(1, 2); catch e, disp(e.message); disp(e.identifier); end")
    _, out = run_script(it, src)
    assert "Too many input arguments." in out
    assert "MATLAB:TooManyInputs" in out


# ── error locations ────────────────────────────────────────────

def test_an_error_in_a_function_names_it_and_its_caller(it):
    src = ("function y = f(a)\n"
           "  y = a;\n"
           "  error('boom');\n"
           "end\n"
           "x = 1;\n"
           "z = f(x);\n")
    error, _ = run_script(it, src)
    assert error.startswith("Error using f (line 3)\nboom")
    assert "Error in line 6" in error
    assert "z = f(x);" in error


def test_a_plain_script_error_keeps_the_short_form(it):
    error, _ = run_script(it, "x = [1 2 3];\nx(7)")
    assert error.startswith("Error in line 2: ")


def test_function_file_errors_name_file_and_line(it, tmp_path):
    (tmp_path / "inner.m").write_text(
        "function y = inner(a)\n  y = a + zz;\nend\n")
    (tmp_path / "ore.m").write_text("x = 3;\ny = 1;\nz = inner(x);\n")
    it.script_folder = str(tmp_path)
    error, _ = run_script(it, "ore", str(tmp_path))
    assert "inner (line 2)" in error
    assert "Error in ore (line 3)" in error
    assert "z = inner(x);" in error


def test_the_python_traceback_is_behind_a_flag(it):
    src = "x = [1 2 3];\nx(7)"
    error, _ = run_script(it, src)
    assert "Traceback" not in error
    it.debug_errors = True
    error, _ = run_script(it, src)
    assert "Traceback (most recent call last)" in error


# ── dotted script names ────────────────────────────────────────

def test_a_dotted_script_name_gets_a_clear_message(it, tmp_path):
    (tmp_path / "C.3.2.m").write_text("x = 1;\n")
    it.script_folder = str(tmp_path)
    result = it.command("C.3.2")
    assert "not a valid MATLAB name" in result.error
    assert "C_3_2.m" in result.error
    assert "not a valid MATLAB name" in it.command("C.3.2.m").error


def test_an_ordinary_syntax_error_is_left_alone(it):
    assert "not a valid MATLAB name" not in it.command("x = (1 +").error


# ── inputParser ────────────────────────────────────────────────

PARSER = """
function out = area(varargin)
  p = inputParser;
  p.FunctionName = 'area';
  addRequired(p, 'w', @isnumeric);
  addOptional(p, 'h', 2, @(x) x > 0);
  addParameter(p, 'unit', 'cm', @ischar);
  addParameter(p, 'scale', 1);
  p.addSwitch('verbose');
  p.KeepUnmatched = true;
  parse(p, varargin{:});
  out = p.Results;
  out.defaults = p.UsingDefaults;
  out.unmatched = p.Unmatched;
end
"""


def test_input_parser_defaults(it):
    it.run_matlab(PARSER)
    assert it.evaluate("area(3).h") == 2
    assert it.evaluate("area(3).unit") == "cm"
    assert list(it.evaluate("area(3).defaults")) == ["h", "unit", "scale",
                                                     "verbose"]


def test_input_parser_optional_then_pairs(it):
    it.run_matlab(PARSER)
    assert it.evaluate("area(3, 5).h") == 5
    assert it.evaluate("area(3, 5, 'unit', 'mm').unit") == "mm"
    # text that names a parameter is not the optional argument
    assert it.evaluate("area(3, 'scale', 4).scale") == 4
    assert it.evaluate("area(3, 'scale', 4).h") == 2


def test_input_parser_switch_unmatched_and_partial_names(it):
    it.run_matlab(PARSER)
    assert it.evaluate("area(3, 'verbose').verbose") is True
    assert it.evaluate("area(3, 'Sca', 7).scale") == 7
    assert it.evaluate("area(3, 'extra', 9).unmatched.extra") == 9


def test_input_parser_results_are_alphabetical(it):
    it.run_matlab(PARSER)
    fields = list(it.evaluate("area(3)"))
    assert fields[:6] == ["h", "scale", "unit", "verbose", "w"] or \
        fields[:5] == sorted(fields[:5], key=str.lower)


def test_input_parser_errors(it):
    it.run_matlab(PARSER)
    assert "Not enough input arguments." in it.command("area()").error
    message = it.command("area('a')").error
    assert "The value of 'w' is invalid" in message
    assert "area:" in message
    assert "It must satisfy the function: @(x) x > 0" in \
        it.command("area(3, -1)").error or "invalid" in \
        it.command("area(3, -1)").error


def test_input_parser_unmatched_is_an_error_by_default(it):
    it.run_matlab("p = inputParser; p.addParameter('tol', 1);")
    message = it.command("p.parse('nope', 1)").error
    assert "'nope' is not a recognized parameter" in message


def test_input_parser_is_a_handle_and_has_a_class(it):
    it.run_matlab("p = inputParser; q = p; q.addParameter('a', 1);")
    assert it.evaluate("class(p)") == "inputParser"
    assert list(it.evaluate("p.Parameters")) == ["a"]


def test_input_parser_validators_that_raise(it):
    it.run_matlab("p = inputParser;\n"
                  "p.addRequired('x', @(v) validateattributes(v, "
                  "{'numeric'}, {'positive'}));")
    assert "The value of 'x' is invalid" in it.command("p.parse(-1)").error
    assert it.command("p.parse(2)").ok


# ── nested functions ───────────────────────────────────────────

NESTED = """
function total = outer(a)
  total = 0;
  function bump()
    total = total + a;
  end
  bump(); bump(); bump();
end
"""


def test_nested_function_shares_the_parents_variables(it):
    it.run_matlab(NESTED)
    assert it.evaluate("outer(4)") == 12


def test_nested_function_own_variables_stay_local(it):
    src = """
function y = outer2()
  y = 1;
  function inner(k)
    t = k * 2;
    y = y + t;
  end
  inner(5);
end
"""
    it.run_matlab(src)
    assert it.evaluate("outer2()") == 11
    assert it.command("t").error


def test_sibling_functions_without_end_are_not_nested(it):
    src = ("function a = one()\n  a = 1;\n"
           "function b = two()\n  b = 2;\n")
    result = it.run_matlab(src)
    assert not any(r.error for r in result)
    assert it.evaluate("one() + two()") == 3


def test_sequential_functions_with_end_are_siblings(it):
    it.run_matlab("function a = one()\n a = 1;\nend\n"
                  "function b = two()\n b = one() + 1;\nend\n")
    assert it.evaluate("two()") == 2
