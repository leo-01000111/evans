# sum

Sum of the elements of a vector, or of each column of a matrix.

## Syntax

    s = sum(A)
    s = sum(A, dim)

## Description

`sum(A)` for a row or column vector returns the sum of its elements as a scalar. For a matrix it sums down each column and returns a row vector with one total per column.

`sum(A, dim)` sums along dimension `dim`: `1` down the columns, giving a row, `2` along the rows, giving a column of row totals. A row vector has one element in each column, so `sum([1 2 3], 1)` is `[1 2 3]` itself; `sum(A, 3)` is `A` too.

A logical array counts its true elements, so `sum(x > 0)` is the number of positive entries. The sum of an integer array is a double holding the true total, without saturating: `sum(int8([100 100]))` is `200` (as in MATLAB R2023a; `prod` does the same). `sum(A, [1 2])` adds over several dimensions at once. The sum of an empty `0`-by-`3` matrix is `[0 0 0]`. Evans does not support `sum(A, 'all')`; use `sum(A(:))` instead.

For an N-D array `sum(A)` runs along the first dimension that is not 1, and `sum(A, 3)` along the third; `mean`, `prod`, `max`, `min`, `cumsum`, `any` and `all` do the same.
## Example

```matlab
x = [1 -2 3 -4];
sum(x)
sum(x > 0)
A = [1 2; 3 4];
sum(A)
```

## See also

[cumsum](cumsum) · [mean](mean) · [max](max) · [diff](diff) · [numel](numel)
