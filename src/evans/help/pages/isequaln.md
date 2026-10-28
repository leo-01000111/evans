# isequaln

True when values are equal, treating NaN as equal to NaN.

## Syntax

    tf = isequaln(A, B)
    tf = isequaln(A, B, C, ...)

## Description

`isequaln` works as `isequal`, except that `NaN` elements in the same places count as equal, also inside cells and structs.

## Example

```matlab
isequal([1 NaN], [1 NaN])
isequaln([1 NaN], [1 NaN])
```

## See also

[isequal](isequal) · [ismember](ismember)
