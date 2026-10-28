# prctile

Percentiles of a vector, or of each column of a matrix.

## Syntax

    Y = prctile(X, p)
    Y = prctile(X, p, dim)
    Y = prctile(..., 'Method', m)

## Description

`prctile(X, p)` returns the `p`-th percentiles of `X`, `p` between 0 and 100. For a vector `X`, `Y` has the shape of `p`. For a matrix, row `i` of `Y` holds the `p(i)`-th percentile of each column; `dim` picks the dimension.

The method is MATLAB's default, `'midpoint'` (once called `'exact'`): the k-th of n sorted values sits at the `100(k-0.5)/n` percentile, values in between are interpolated linearly, and percentiles outside that range take the smallest or largest value. `'inclusive'` and `'exclusive'` are also supported. `NaN` values are ignored.

Evans does not support the `'approximate'` method, `'all'` or a vector `dim`.

## Example

```matlab
prctile([1 2 3 4], [25 50 75])
```

## See also

[quantile](quantile) · [sort](sort) · [mean](mean) · [max](max)
