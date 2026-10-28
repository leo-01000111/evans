# corrcoef

Correlation coefficients of the columns of a matrix, or of two vectors.

## Syntax

    R = corrcoef(A)
    R = corrcoef(x, y)
    [R, P] = corrcoef(...)

## Description

`corrcoef(A)` treats each column of `A` as a variable and returns the matrix of Pearson correlation coefficients; the diagonal is 1. `corrcoef(x, y)` correlates two vectors and returns a 2-by-2 matrix.

`[R, P] = corrcoef(...)` also returns p-values for the hypothesis of no correlation, from a t statistic with `N-2` degrees of freedom.

Evans does not support the `RL`/`RU` bound outputs or the `'Alpha'` and `'Rows'` options.

## Example

```matlab
x = [1 2 3 4 5];
y = [2 1 4 3 5];
[R, P] = corrcoef(x, y)
```

## See also

[cov](cov) · [var](var) · [regress](regress)
