# normpdf

Probability density of the normal distribution.

## Syntax

    y = normpdf(x)
    y = normpdf(x, mu)
    y = normpdf(x, mu, sigma)

## Description

`normpdf(x, mu, sigma)` is `exp(-(x-mu).^2/(2*sigma^2)) / (sigma*sqrt(2*pi))`, element by element; `mu` defaults to 0 and `sigma` to 1. The arguments can be scalars or arrays of the same size (scalars expand).

Where `sigma` is not positive, the result is `NaN`.

## Example

```matlab
x = -3:0.1:3;
plot(x, normpdf(x), x, normpdf(x, 1, 0.5))
```

## See also

[normcdf](normcdf) · [norminv](norminv) · [rand](rand)
