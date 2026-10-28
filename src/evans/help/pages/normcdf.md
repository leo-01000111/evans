# normcdf

Cumulative distribution function of the normal distribution.

## Syntax

    p = normcdf(x)
    p = normcdf(x, mu, sigma)
    p = normcdf(..., 'upper')

## Description

`normcdf(x, mu, sigma)` is the probability that a normal variable with mean `mu` (default 0) and standard deviation `sigma` (default 1) is at most `x`, element by element. `'upper'` gives the upper tail, `1 - normcdf(x)`, computed accurately for large `x`.

Where `sigma` is not positive, the result is `NaN`. Evans does not support the confidence-bound outputs `[p, plo, pup]`.

## Example

```matlab
normcdf(1.96)
normcdf([-1 1])
normcdf(3, 0, 1, 'upper')
```

## See also

[normpdf](normpdf) · [norminv](norminv) · [ttest](ttest)
