# confint

Confidence bounds on a fit's coefficients.

## Syntax

    ci = confint(f)
    ci = confint(f, level)

## Description

A 2-by-p matrix: the lower bounds in the first row and the upper in the second, one column per coefficient, at confidence `level` (0.95 by default). They come from the Jacobian at the fit and Student's t, as in MATLAB. With no more points than coefficients the bounds are NaN.

## Example

```matlab
x = (0:9)';  y = 2*x + 1 + 0.1*sin(7*x);
f = fit(x, y, 'poly1');
ci = confint(f)
```

## See also

[coeffvalues](coeffvalues) · [fit](fit)
