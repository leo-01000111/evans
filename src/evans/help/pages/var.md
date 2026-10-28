# var

Variance of a vector, or of each column of a matrix.

## Syntax

    v = var(A)
    v = var(A, w)
    v = var(A, w, dim)
    v = var(A, w, 'all')
    v = var(..., 'omitnan')

## Description

`var(A)` of a row or column vector is a scalar; of a matrix, a row vector with the variance of each column. It normalises by `N-1` (by `N` when there is only one element).

`w = 1` normalises by `N` instead; `w = 0` or `[]` is the default. `dim` works along that dimension (`2`: one value per row, a column). `'all'` takes every element; `'omitnan'` drops `NaN` values (otherwise a `NaN` gives `NaN`).

Evans does not support a weight vector for `w`.

## Example

```matlab
x = [2 4 4 4 5 5 7 9];
var(x)
var(x, 1)
var([1 2; 3 5])
```

## See also

[mean](mean) · [cov](cov) · [mode](mode) · [sum](sum)
