# coeffnames

The names of a fit's coefficients.

## Syntax

    names = coeffnames(f)

## Description

A column cell of the coefficient names of `f`, the result of [fit](fit): `p1`, `p2`, … for a polynomial, `a`, `b`, … for the exponential, power and sine models.

## Example

```matlab
f = fit((1:5)', exp(0.3*(1:5))', 'exp1');
coeffnames(f)
```

## See also

[coeffvalues](coeffvalues) · [confint](confint) · [fit](fit)
