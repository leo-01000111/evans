# isfield

True when a struct has a field of the given name.

## Syntax

    tf = isfield(s, name)
    tf = isfield(s, names)

## Description

`isfield(s, name)` is true when the struct (or struct array) `s` has a field called `name`. It is false when `s` is not a struct.

With a cell of names, the result is a logical array the shape of the cell, one answer per name.

## Example

```matlab
s = struct('gain', 2, 'delay', 0.1);
isfield(s, 'gain')
```

## See also

[rmfield](rmfield) · [getfield](getfield) · [setfield](setfield) · [orderfields](orderfields)
