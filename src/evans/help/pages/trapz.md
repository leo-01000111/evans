# trapz

Integrate sampled data with the trapezoidal rule.

## Syntax

    Q = trapz(Y)
    Q = trapz(X, Y)
    Q = trapz(Y, dim)
    Q = trapz(X, Y, dim)

## Description

`trapz(Y)` integrates the samples `Y` assuming a spacing of 1. For a vector it returns a number; `trapz([1 2 3])` is 4, and a single number gives 0. For a matrix it works down each column and returns a row, so for `[1 2 3; 4 5 6]` it returns `[2.5 3.5 4.5]`.

`trapz(X, Y)` uses the sample points `X`, which need not be evenly spaced. If `X` is a scalar it is the spacing: `trapz(0.5, [1 2 3])` is 2. If `Y` is a matrix, `X` is a vector with one point per row. Reversed points give a negative area: `trapz([2 1 0], [1 2 3])` is -4. A vector `X` must have one point per sample along the dimension being integrated; `trapz([0 1 2], [1 2])` stops with an error.

`trapz(Y, dim)` and `trapz(X, Y, dim)` integrate along dimension `dim`. Along dimension 2 the result is a column, one value per row: `trapz([1 2 3; 4 5 6], 2)` is `[4; 10]`, and `trapz([0 1 3], [1 2 3; 4 5 6], 2)` is `[6.5; 15.5]`.

## Example

```matlab
x = linspace(0, pi, 101);
Q = trapz(x, sin(x))
```

The exact integral is 2; the trapezoidal sum with 101 points prints 1.9998.

## See also

[cumsum](cumsum) · [integral](integral) · [quadgk](quadgk) · [diff](diff) · [sum](sum)
