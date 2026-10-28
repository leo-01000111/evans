# lsqcurvefit

Nonlinear least-squares fit of a model's parameters to data.

## Syntax

    x = lsqcurvefit(fun, x0, xdata, ydata)
    x = lsqcurvefit(fun, x0, xdata, ydata, lb, ub)
    x = lsqcurvefit(fun, x0, xdata, ydata, lb, ub, options)
    [x, resnorm, residual, exitflag, output] = lsqcurvefit(...)

## Description

`lsqcurvefit` finds the parameters `x` that minimise `sum((fun(x, xdata) - ydata).^2)`, starting from `x0`, within the bounds `lb` and `ub` (`[]` for none). `resnorm` is that sum of squares at the solution and `residual` is `fun(x, xdata) - ydata`. Options come from `optimoptions`.

Bounds are the only constraints Evans supports, and at most five outputs.

## Example

```matlab
model = @(p, t) p(1)*exp(-p(2)*t);
t = 0:0.5:4;
y = 3*exp(-0.7*t);
p = lsqcurvefit(model, [1 1], t, y)
```

## See also

[fit](fit)
