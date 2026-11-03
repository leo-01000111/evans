# lsqnonlin

Solve a nonlinear least-squares problem.

## Syntax

    x = lsqnonlin(fun, x0)
    x = lsqnonlin(fun, x0, lb, ub)
    x = lsqnonlin(fun, x0, lb, ub, options)
    [x, resnorm, residual, exitflag, output] = lsqnonlin(...)

## Description

`lsqnonlin` finds the `x` that minimises `sum(fun(x).^2)`, where `fun` returns the vector of residuals. `lb` and `ub` bound `x` (`[]` for none). `resnorm` is the sum of squares at `x` and `residual` is `fun(x)`.

Evans takes bounds as the only constraints. [lsqcurvefit](lsqcurvefit) is the same solver written for fitting a model to data.

## Example

```matlab
t = (0:5)';  y = 3*exp(-0.4*t);
res = @(p) p(1)*exp(-p(2)*t) - y;
p = lsqnonlin(res, [1 1], [], [], optimoptions('lsqnonlin', 'Display', 'off'))
```

## See also

[lsqcurvefit](lsqcurvefit) · [fminunc](fminunc) · [optimoptions](optimoptions)
