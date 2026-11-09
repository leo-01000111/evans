"""``classdef``: value and handle classes, inheritance, operators, display."""

import pytest

from evans.console.interpreter import Interpreter

POINT = """\
classdef Point
    properties
        x = 0
        y = 0
    end
    properties (Dependent)
        r
    end
    properties (Constant)
        Origin = 0
    end
    methods
        function obj = Point(x, y)
            if nargin > 0
                obj.x = x;
                obj.y = y;
            end
        end
        function r = get.r(obj)
            r = sqrt(obj.x^2 + obj.y^2);
        end
        function obj = move(obj, dx, varargin)
            obj.x = obj.x + dx;
            if ~isempty(varargin)
                obj.y = obj.y + varargin{1};
            end
        end
        function p = plus(a, b)
            p = Point(a.x + b.x, a.y + b.y);
        end
        function disp(obj)
            fprintf('Point(%g, %g)\\n', obj.x, obj.y);
        end
    end
    methods (Static)
        function p = unit()
            p = Point(1, 0);
        end
    end
end
"""

COUNTER = """\
classdef Counter < handle
    properties
        n = 0
    end
    properties (SetAccess = private)
        log = {}
    end
    properties (Access = private)
        secret = 42
    end
    methods
        function inc(obj)
            obj.n = obj.n + 1;
            obj.log{end+1} = obj.n;
        end
        function s = peek(obj)
            s = obj.secret;
        end
        function delete(obj)
            disp('bye');
        end
    end
end
"""

ANIMAL = """\
classdef Animal
    properties
        name
    end
    methods
        function obj = Animal(name)
            obj.name = name;
        end
        function s = speak(obj)
            s = [obj.name ' makes a sound'];
        end
        function s = describe(obj)
            s = ['I am ' obj.name];
        end
    end
end
"""

DOG = """\
classdef Dog < Animal
    properties
        tricks = 0
    end
    methods
        function obj = Dog(name)
            obj = obj@Animal(name);
            obj.tricks = 3;
        end
        function s = speak(obj)
            s = [speak@Animal(obj) ': woof'];
        end
    end
end
"""

COLOR = """\
classdef Color
    enumeration
        Red (1, 0, 0)
        Green (0, 1, 0)
    end
    properties
        r
        g
        b
    end
    methods
        function obj = Color(r, g, b)
            obj.r = r; obj.g = g; obj.b = b;
        end
    end
end
"""

BUTTON = """\
classdef Button < handle
    events
        Pressed
    end
    methods
        function press(obj)
            notify(obj, 'Pressed');
        end
    end
end
"""


VALIDATED = """classdef Valid
    properties
        items = []
        level = 1
    end
    methods
        function obj = Valid(varargin)
            obj.items = varargin;
        end
        function obj = set.level(obj, v)
            if v < 0
                error('Valid:neg', 'level must be non-negative');
            end
            obj.level = v;
        end
        function n = count(obj)
            n = numel(obj.items) + nargin - 1;
        end
    end
end
"""


@pytest.fixture
def it(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name, text in [("Point", POINT), ("Counter", COUNTER),
                       ("Animal", ANIMAL), ("Dog", DOG), ("Color", COLOR),
                       ("Button", BUTTON), ("Valid", VALIDATED)]:
        (tmp_path / f"{name}.m").write_text(text)
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


def out(it, source) -> str:
    return run(it, source).output


# ── value classes ──────────────────────────────────────────────

def test_constructor_and_properties(it):
    run(it, "p = Point(3, 4);")
    assert value(it, "p.x") == 3
    assert value(it, "p.r") == 5            # a Dependent property's getter
    assert value(it, "class(p)") == "Point"
    assert value(it, "Point.Origin") == 0


def test_default_constructor_with_no_arguments(it):
    run(it, "p = Point;")
    assert value(it, "p.x") == 0


def test_value_semantics_copy_on_assignment(it):
    run(it, "p = Point(1, 1); q = p; q.x = 9;")
    assert value(it, "p.x") == 1
    assert value(it, "q.x") == 9


def test_a_method_returning_the_object_leaves_the_original(it):
    run(it, "p = Point(1, 1); q = p.move(5, 2); r = move(p, 1);")
    assert value(it, "p.x") == 1
    assert value(it, "q.x") == 6 and value(it, "q.y") == 3
    assert value(it, "r.x") == 2


def test_static_method_and_operator_overload(it):
    run(it, "s = Point.unit() + Point(2, 5);")
    assert value(it, "s.x") == 3 and value(it, "s.y") == 5


def test_overloaded_disp_and_display(it):
    assert "Point(1, 2)" in out(it, "disp(Point(1, 2))")
    assert "Point(1, 2)" in out(it, "p = Point(1, 2)")


def test_default_display(it):
    text = out(it, "q = Counter();\nq")
    assert "Counter with properties:" in text
    assert "n: 0" in text
    assert "secret" not in text


def test_properties_methods_and_predicates(it):
    run(it, "p = Point(1, 2);")
    names = value(it, "properties(p)")
    assert list(names) == ["x", "y", "r", "Origin"]
    assert "move" in list(value(it, "methods(p)"))
    assert value(it, "ismethod(p, 'move')") is True
    assert value(it, "isprop(p, 'x')") is True
    assert value(it, "isprop(p, 'nope')") is False
    assert value(it, "isobject(p)") is True
    assert value(it, "isa(p, 'Point')") is True


def test_unknown_property_message(it):
    run(it, "p = Point(1, 2);")
    assert "Unrecognized method, property, or field 'z' for class " \
        "'Point'" in error(it, "p.z")


# ── handle classes ─────────────────────────────────────────────

def test_handles_share_state(it):
    run(it, "c = Counter(); d = c; d.inc(); inc(c);")
    assert value(it, "c.n") == 2
    assert value(it, "numel(c.log)") == 2
    assert value(it, "c == d") is True
    assert value(it, "isa(c, 'handle')") is True


def test_access_control(it):
    run(it, "c = Counter();")
    assert value(it, "c.peek()") == 42
    assert "cannot get the 'secret' property" in error(it, "c.secret")
    assert "cannot set the 'log' property" in error(it, "c.log = 1;")


def test_delete_and_isvalid(it):
    run(it, "c = Counter(); d = c;")
    assert "bye" in out(it, "delete(c)")
    assert value(it, "isvalid(d)") is False
    assert "Invalid or deleted" in error(it, "d.n")


def test_events(it):
    run(it, "b = Button(); "
            "addlistener(b, 'Pressed', @(s, e) disp(e.EventName));")
    assert "Pressed" in out(it, "b.press()")


# ── inheritance ────────────────────────────────────────────────

def test_inheritance_and_super_calls(it):
    run(it, "d = Dog('Rex');")
    assert value(it, "d.speak()") == "Rex makes a sound: woof"
    assert value(it, "describe(d)") == "I am Rex"
    assert value(it, "d.tricks") == 3
    assert value(it, "isa(d, 'Animal')") is True
    assert value(it, "isa(d, 'Dog')") is True
    assert value(it, "isa(Animal('x'), 'Dog')") is False


# ── enumeration ────────────────────────────────────────────────

def test_enumeration(it):
    assert value(it, "Color.Green.g") == 1
    assert value(it, "Color.Red == Color.Red") is True
    assert value(it, "Color.Red == Color.Green") is False


# ── odds and ends ──────────────────────────────────────────────

def test_classdef_cannot_be_typed_at_the_prompt(it):
    assert "classdef can only be defined in a file" in error(
        it, "classdef Foo\nend")


def test_set_method_validates_and_nested_writes_copy(it):
    run(it, "v = Valid(1, 2, 3); w = v; w.level = 5; w.items{2} = 'x';")
    assert value(it, "v.level") == 1
    assert value(it, "w.level") == 5
    assert value(it, "v.items{2}") == 2
    assert value(it, "w.items{2}") == "x"
    assert "level must be non-negative" in error(it, "v.level = -1;")


def test_varargin_and_nargin_in_methods(it):
    run(it, "v = Valid(1, 2, 3);")
    assert value(it, "v.count()") == 3
    assert value(it, "count(v)") == 3


def test_constant_property_is_read_only(it):
    assert "Constant" in error(it, "p = Point(1, 2); p.Origin = 3;")
