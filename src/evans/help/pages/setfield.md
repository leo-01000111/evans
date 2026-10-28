# setfield

A copy of a struct with a field set to a value.

## Syntax

    s = setfield(s, name, value)
    s = setfield(s, name1, name2, ..., value)

## Description

`setfield(s, name, value)` returns `s` with `s.(name) = value`, adding the field if it is new; several names set a nested field. The input is not changed unless you assign the result back to it.

Evans does not support the index arguments `{k}`, or setfield of a struct array with more than one element; write `s(k).name = value` instead.

## Example

```matlab
s = struct('gain', 2);
s = setfield(s, 'delay', 0.1)
```

## See also

[getfield](getfield) · [isfield](isfield) · [rmfield](rmfield)
