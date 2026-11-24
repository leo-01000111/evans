# trapz

Integrate sampled data with the trapezoidal rule.

## Syntax

    Q = trapz(Y)
    Q = trapz(X, Y)
    Q = trapz(X, Y, dim)

## Description

`trapz(Y)` integrates the samples `Y` assuming a spacing of 1. For a vector it returns a number; `trapz([1 2 3])` is 4. For a matrix it works down each column and returns a row, so for `[1 2 3; 4 5 6]` it returns `[2.5 3.5 4.5]`.

`trapz(X, Y)` uses the sample points `X`, which need not be evenly spaced. If `X` is a scalar it is the spacing: `trapz(0.5, [1 2 3])` is 2. If `Y` is a matrix, `X` is a vector with one point per row. `trapz(X, Y, dim)` integrates along dimension `dim`. Reversed points give a negative area: `trapz([2 1 0], [1 2 3])` is -4.

Limits of Evans:

- With `dim` equal to 2 the result is a row vector, not a column: `trapz([0 1 3], [1 2 3; 4 5 6], 2)` prints `6.5000 15.5000` as one row.
- `trapz(Y, dim)`, with the dimension but no `X`, does not work: `trapz(A, 2)` fails with `IndexError: list assignment index out of range`, because the 2 is taken as `Y`. Pass a spacing instead: `trapz(1, A, 2)`.
- A single number, `trapz(5)`, fails the same way.
- The lengths of `X` and `Y` are not compared: `trapz([0 1 2], [1 2])` returns 3 without an error.

## Example

```matlab
x = linspace(0, pi, 101);
Q = trapz(x, sin(x))
```

The exact integral is 2; the trapezoidal sum with 101 points prints 1.9998.

## See also

[cumsum](cumsum) · [integral](integral) · [quadgk](quadgk) · [diff](diff) · [sum](sum)
