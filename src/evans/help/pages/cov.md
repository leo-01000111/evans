# cov

Covariance of a vector, of the columns of a matrix, or of two vectors.

## Syntax

    C = cov(x)
    C = cov(A)
    C = cov(x, y)
    C = cov(..., w)

## Description

`cov(x)` of a vector is its variance. `cov(A)` treats each row of `A` as an observation and each column as a variable, and returns the covariance matrix (one row and column per variable).

`cov(x, y)` treats `x` and `y` (any shape, the same number of elements) as two variables and returns the 2-by-2 matrix `[var(x) c; c var(y)]`, as MATLAB does.

It normalises by `N-1`; `w = 1` normalises by `N`. Evans does not support `'omitrows'` or `'partialrows'`.

## Example

```matlab
x = [1 2 3 4];
y = [2 4 5 9];
C = cov(x, y)
```

## See also

[var](var) · [corrcoef](corrcoef) · [mean](mean)
