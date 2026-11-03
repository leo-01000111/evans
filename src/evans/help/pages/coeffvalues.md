# coeffvalues

The coefficient values of a fit.

## Syntax

    c = coeffvalues(f)

## Description

A row of the fitted coefficients of `f`, the result of [fit](fit), in the order [coeffnames](coeffnames) lists them.

## Example

```matlab
x = (0:5)';  y = 2*x + 1;
f = fit(x, y, 'poly1');
c = coeffvalues(f)
```

## See also

[coeffnames](coeffnames) · [confint](confint) · [fit](fit)
