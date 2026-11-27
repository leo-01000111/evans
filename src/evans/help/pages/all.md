# all

Test whether every element is nonzero.

## Syntax

    tf = all(x)
    tf = all(x, dim)

## Description

`all(x)` is true (1, of class `logical`) when no element of `x` is zero, and false (0) otherwise. A `NaN` counts as nonzero, as does `Inf`, a negative number or a complex number. Characters count by their code, so `all('abc')` is 1. An empty vector gives 1: `all([])`, `all(zeros(1,0))` and `all('')` are 1.

For a vector, `all(x)` is a single value. The usual use is on a comparison: `all(x > 0)`. For a matrix, `all(x)` tests each column and returns a row: `all([1 1; 0 1])` is `[0 1]`, and `all(zeros(0,3))` is `[1 1 1]`. To test every element of a matrix, use `all(all(A))` or `all(A(:))`. An array with three or more dimensions is tested down its first dimension that is not 1, and keeps the rest.

`all(x, dim)` tests along dimension `dim` and keeps the other dimensions: for `[1 1; 0 1]`, `all(A, 1)` is the row `[0 1]` and `all(A, 2)` is the column `[1; 0]`. A `dim` above the number of dimensions gives the array itself as 0 and 1. For an array with more than two dimensions, `dim` may also be a vector such as `[1 2]` to test over several dimensions at once. `dim` of 0 stops with "Dimension argument must be a positive integer scalar."

Limits of Evans:

- `all(x, 'all')` does not work: it stops with `ValueError: invalid literal for int() with base 10: 'all'`. A text `dim` fails the same way, and a fractional `dim` such as 1.5 is silently rounded down.
- With `dim` 3 or more on a matrix, the result is the array itself with each element as 0 or 1.
- Wrong argument counts stop with an internal `TypeError` message, not a MATLAB-style one.

## Example

```matlab
x = [2 4 6];
all(x > 0)
all(x > 3)
all([1 1; 0 1])
all([1 1; 0 1], 2)
```

The four results are 1, 0, the row `0 1` and the column `1; 0`.

## See also

[find](find) · [nnz](nnz) · [isequal](isequal) · [sum](sum)
