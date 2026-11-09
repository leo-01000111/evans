# classdef

Classes: a `.m` file that starts with `classdef` defines a class you can use by name.

## What works

Put `Name.m` in the current folder or on the path and call `Name(...)`. Typing a `classdef` at the prompt or in a script is an error, as in MATLAB.

    classdef Account < handle
        properties
            balance = 0
        end
        properties (SetAccess = private)
            history = {}
        end
        methods
            function obj = Account(start)
                if nargin > 0
                    obj.balance = start;
                end
            end
            function deposit(obj, amount)
                obj.balance = obj.balance + amount;
                obj.history{end+1} = amount;
            end
        end
    end

- **Properties** have defaults and the attributes `Access`, `GetAccess`, `SetAccess`, `Constant`, `Dependent` and `Hidden`. A `get.Name` method computes a property when it is read, a `set.Name` method checks it when it is written. Size and class lines such as `x (1,1) double = 0` are accepted but not enforced.
- **Methods** are called `obj.method(args)` or `method(obj, args)`. A `Static` method is called `Class.method(args)`; a `Constant` property is `Class.Name`. `nargin`, `nargout` and `varargin` work as in functions.
- **Value classes** copy on assignment: after `b = a; b.x = 1`, `a` is unchanged. A method that changes the object returns it (`obj = move(obj, 1)`).
- **Handle classes** (`< handle`) are references: every name holding the object sees a change. `delete(h)` calls the class's `delete` method and makes every reference invalid (`isvalid`). `matlab.mixin.Copyable` adds `copy`.
- **Inheritance**: `classdef B < A`, constructors call `obj = obj@A(args)` (without it, `A` is built with no arguments first), and `speak@A(obj)` calls the overridden method.
- **Operators**: define `plus`, `minus`, `times`, `mtimes`, `rdivide`, `mrdivide`, `power`, `mpower`, `eq`, `ne`, `lt`, `le`, `gt`, `ge`, `uminus`, `transpose`, `ctranspose`, and `disp` or `display` for how the object prints. Any other method name also works for functions such as `size` and `numel`.
- **Events** declared in an `events` block work with `addlistener` and `notify` on handle objects. **Enumerations** work for members with constructor arguments (`Color.Red`).
- `class`, `isa`, `properties`, `methods`, `ismethod`, `isprop`, `isobject`, `isvalid` accept objects.

## What is left out

Arrays of objects (`[a b]`, `objs(2)`), `subsref`/`subsasgn` overloads, property validation and `AbortSet`, `dynamicprops`, class folders (`@Name`, `+pkg`), methods defined in separate files, and `metaclass`.

## See also

[properties](properties) · [methods](methods) · [ismethod](ismethod) · [isprop](isprop) · [isvalid](isvalid) · [isobject](isobject) · [addlistener](addlistener) · [notify](notify) · [copy](copy)
