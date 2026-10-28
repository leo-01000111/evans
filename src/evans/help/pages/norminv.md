# norminv

Inverse of the normal cumulative distribution function.

## Syntax

    x = norminv(p)
    x = norminv(p, mu, sigma)

## Description

`norminv(p, mu, sigma)` returns the value `x` with `normcdf(x, mu, sigma) = p`, element by element; `mu` defaults to 0, `sigma` to 1. `p` outside `[0, 1]` gives `NaN`; `p = 0` and `p = 1` give `-Inf` and `Inf`.

Where `sigma` is not positive, the result is `NaN`.

## Example

```matlab
norminv(0.975)
norminv([0.05 0.95], 10, 2)
```

## See also

[normcdf](normcdf) · [normpdf](normpdf) · [prctile](prctile)
