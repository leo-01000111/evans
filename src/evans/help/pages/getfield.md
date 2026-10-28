# getfield

The value of a struct field named by a string.

## Syntax

    v = getfield(s, name)
    v = getfield(s, name1, name2, ...)

## Description

`getfield(s, name)` is `s.(name)`; several names reach nested fields, so `getfield(s, 'a', 'b')` is `s.a.b`.

Evans does not support the index arguments `getfield(s, {k}, name)`, or getfield of a struct array with more than one element; write `s(k).name` instead.

## Example

```matlab
s.motor.gain = 2.5;
g = getfield(s, 'motor', 'gain')
```

## See also

[setfield](setfield) · [isfield](isfield) · [rmfield](rmfield)
