# kurtosis

Sample kurtosis of a vector, or of each column of a matrix.

## Syntax

    k = kurtosis(X)
    k = kurtosis(X, flag)
    k = kurtosis(X, flag, dim)

## Description

`kurtosis(X)` is the fourth central moment divided by the square of the variance (both with `1/N`); a normal distribution gives 3 (it is not the excess kurtosis). `flag = 1`, the default, is the biased estimate; `flag = 0` corrects for bias and needs at least 4 values.

A matrix gives one value per column (a row); `dim` picks the dimension. `NaN` values are ignored.

## Example

```matlab
kurtosis([1 2 3 10])
kurtosis([1 2 3 10], 0)
```

## See also

[skewness](skewness) · [var](var) · [mean](mean)
