# skewness

Sample skewness of a vector, or of each column of a matrix.

## Syntax

    y = skewness(X)
    y = skewness(X, flag)
    y = skewness(X, flag, dim)

## Description

`skewness(X)` is the third central moment divided by the cube of the standard deviation (both with `1/N`): `flag = 1`, the default, is the biased estimate. `flag = 0` corrects for bias, multiplying by `sqrt(N(N-1))/(N-2)`; it needs at least 3 values.

A matrix gives one value per column (a row); `dim` picks the dimension. `NaN` values are ignored.

## Example

```matlab
skewness([1 2 3 10])
skewness([1 2 3 10], 0)
```

## See also

[kurtosis](kurtosis) · [var](var) · [mean](mean)
