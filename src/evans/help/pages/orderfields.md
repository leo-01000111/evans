# orderfields

Reorder the fields of a struct.

## Syntax

    s = orderfields(s)
    s = orderfields(s, names)
    s = orderfields(s, perm)
    s = orderfields(s, s2)
    [s, perm] = orderfields(...)

## Description

`orderfields(s)` sorts the fields by name in character-code order, so uppercase names come before lowercase ones (`B` before `a`).

`orderfields(s, names)` uses the order of a cell of names, `orderfields(s, perm)` a permutation vector of field positions, and `orderfields(s, s2)` the field order of another struct `s2`. Each must name exactly the fields of `s`.

`[s, perm] = orderfields(...)` also returns a column vector: `perm(k)` is the old position of the k-th new field.

## Example

```matlab
s = struct('b', 1, 'B', 2, 'a', 3);
[t, perm] = orderfields(s)
```

## See also

[rmfield](rmfield) · [isfield](isfield) · [sort](sort)
