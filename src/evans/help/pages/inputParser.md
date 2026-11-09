# inputParser

Check a function's inputs: required, optional and name-value.

## Syntax

    p = inputParser
    addRequired(p, name, validator)
    addOptional(p, name, default, validator)
    addParameter(p, name, default, validator)
    addSwitch(p, name)
    parse(p, args...)
    p.Results    p.Unmatched    p.UsingDefaults

## Description

`inputParser` makes a parser you describe once and run on `varargin`. Declare required arguments first, then optional positional ones, then name-value pairs; `parse` fills `p.Results`, a struct with a field per name (alphabetical, as in MATLAB). Anything not given takes its default and is listed in `p.UsingDefaults`.

The methods can be written either way: `addRequired(p, 'x')` or `p.addRequired('x')`. A validator is a handle that returns true or false, or one that raises an error itself (`validateattributes`). A false result says `The value of 'x' is invalid. It must satisfy the function: …`.

Properties you can set: `FunctionName` (put in front of error messages), `KeepUnmatched` (collect unknown name-value pairs in `p.Unmatched` instead of failing), `CaseSensitive` (default false), `PartialMatching` (default true: a unique prefix of a name is enough) and `StructExpand` (default true: a struct argument is read as name-value pairs).

An optional argument that is text and spells a parameter name is read as that parameter, so `f(3, 'scale', 2)` skips the optional ones. `addParamValue` is an old spelling of `addParameter`. `addSwitch` takes no value: naming it sets it true.

Not in Evans: `disp` of a parser shows its properties only, and `p.Results` is a plain struct rather than a read-only one.

## Example

```matlab
p = inputParser;
addRequired(p, 'w', @isnumeric);
addOptional(p, 'h', 2);
addParameter(p, 'unit', 'cm', @ischar);
parse(p, 3, 'unit', 'mm');
p.Results
p.UsingDefaults
```

## See also

[validateattributes](validateattributes) · [nargin](nargin) · [parse](parse)
