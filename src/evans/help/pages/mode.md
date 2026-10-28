# mode

Most frequent value of a vector, or of each column of a matrix.

## Syntax

    M = mode(A)
    M = mode(A, dim)
    [M, F] = mode(...)

## Description

`mode(A)` returns the value that appears most often. When several values tie, it returns the smallest of them. For a matrix it works down each column and returns a row vector; `dim` picks the dimension.

`[M, F] = mode(A)` also returns how many times `M` appears. `NaN` values are ignored; if nothing is left, `M` is `NaN` and `F` is `0`.

Evans does not support the third output `C` (the cell of all tied values).

## Example

```matlab
[M, F] = mode([3 1 1 3 2])
```

## See also

[mean](mean) · [var](var) · [max](max) · [sort](sort)
