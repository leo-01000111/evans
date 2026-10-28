# quantile

Quantiles of a vector, or of each column of a matrix.

## Syntax

    Y = quantile(X, p)
    Y = quantile(X, N)
    Y = quantile(X, p, dim)
    Y = quantile(..., 'Method', m)

## Description

`quantile(X, p)` is [prctile](prctile) with `p` as cumulative probabilities between 0 and 1: `quantile(X, 0.5)` is `prctile(X, 50)`. Same method (`'midpoint'`), same shapes.

`quantile(X, N)` with an integer `N > 1` returns `N` quantiles at the probabilities `(1:N)/(N+1)`.

Evans does not support the `'approximate'` method.

## Example

```matlab
quantile([2 5 6 10 11 13], [0.25 0.5 0.75])
```

## See also

[prctile](prctile) · [sort](sort) · [mean](mean)
