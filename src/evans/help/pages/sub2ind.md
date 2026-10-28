# sub2ind

Convert row and column subscripts to linear indices.

## Syntax

    ind = sub2ind(sz, row, col)
    ind = sub2ind(sz, i1, i2, ..., in)

## Description

`sub2ind(sz, row, col)` returns the linear index of element `(row, col)` of an array of size `sz`, counting down the columns as MATLAB stores arrays: `row + (col-1)*sz(1)`. `row` and `col` can be arrays of the same size; the result has that size.

A subscript outside `sz` is an error, "Out of range subscript."

## Example

```matlab
sub2ind([3 4], 2, 3)
sub2ind([3 4], [1 2 3], [1 1 4])
```

## See also

[ind2sub](ind2sub) · [size](size) · [find](find)
