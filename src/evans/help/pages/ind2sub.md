# ind2sub

Convert linear indices to row and column subscripts.

## Syntax

    [row, col] = ind2sub(sz, ind)
    [i1, i2, ..., in] = ind2sub(sz, ind)

## Description

`[row, col] = ind2sub(sz, ind)` returns the subscripts of the elements at linear index `ind` in an array of size `sz` (counted down the columns). `ind` can be an array; each output has its size.

With fewer outputs than dimensions, the last output indexes into the remaining dimensions together; with one output, `ind2sub` returns `ind` itself, as MATLAB does. An index past `prod(sz)` is an error.

## Example

```matlab
[row, col] = ind2sub([3 4], [2 7 12])
```

## See also

[sub2ind](sub2ind) · [find](find) · [size](size)
