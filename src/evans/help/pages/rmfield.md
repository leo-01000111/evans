# rmfield

Remove fields from a struct.

## Syntax

    s = rmfield(s, name)
    s = rmfield(s, names)

## Description

`rmfield(s, name)` returns `s` without the field `name`; `names` can be a cell of names, to remove several. For a struct array the fields go from every element.

Naming a field that does not exist is an error: "A field named 'x' doesn't exist." The original struct is not changed unless you assign the result back to it.

## Example

```matlab
s = struct('a', 1, 'b', 2, 'c', 3);
s = rmfield(s, 'b')
t = rmfield(s, {'a', 'c'})
```

## See also

[isfield](isfield) · [orderfields](orderfields) · [setfield](setfield) · [struct2cell](struct2cell)
