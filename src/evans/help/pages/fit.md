# fit

Fit a library curve model to data.

## Syntax

    f = fit(x, y, fittype)
    [f, gof] = fit(x, y, fittype)
    f = fit(..., Name, Value)

## Description

`fittype` is a library model name: `'poly1'` to `'poly9'`, `'exp1'` (`a*exp(b*x)`), `'exp2'`, `'power1'` (`a*x^b`) and `'sin1'` (`a1*sin(b1*x+c1)`). Polynomials are solved exactly by linear least squares; the others are found by nonlinear least squares from a starting guess (or `'StartPoint'`), with `'Lower'` and `'Upper'` bounds.

The result displays like MATLAB's, evaluates as `f(xq)`, has its coefficients as fields (`f.a`), and works with `coeffvalues` and `confint`. `gof` holds `sse`, `rsquare`, `dfe`, `adjrsquare` and `rmse`.

Custom equations, robust fitting, `'Normalize'`, surface fits and the `cftool` app are not supported.

## Example

```matlab
x = (0:0.5:3)';
y = 2*exp(0.8*x);
[f, gof] = fit(x, y, 'exp1');
f.b
gof.rsquare
```

## See also

[lsqcurvefit](lsqcurvefit)
