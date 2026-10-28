# isequal

True when values are equal in size and content.

## Syntax

    tf = isequal(A, B)
    tf = isequal(A, B, C, ...)

## Description

`isequal(A, B)` is true when `A` and `B` have the same size and the same values. Numbers, logicals and characters compare by value, so `isequal(1, true)` and `isequal('a', 97)` are true, but a row and a column of the same numbers are not equal.

Cells compare element by element; structs compare field by field, in any field order. With more inputs, all must be equal.

`NaN` is not equal to itself; use `isequaln` to treat `NaN`s as equal. Evans does not compare systems (`tf`, `ss`) with isequal; compare their data instead.

## Example

```matlab
isequal([1 2 3], [1 2 3])
isequal([1 2], [1; 2])
isequal(struct('a', 1, 'b', 2), struct('b', 2, 'a', 1))
```

## See also

[isequaln](isequaln) · [ismember](ismember) · [size](size)
