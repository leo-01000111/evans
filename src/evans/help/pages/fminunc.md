# fminunc

Find a local minimum of a function with no constraints.

## Syntax

    x = fminunc(fun, x0)
    x = fminunc(fun, x0, options)
    [x, fval, exitflag, output, grad, hessian] = fminunc(...)

## Description

`fminunc` starts at `x0` and descends to a local minimum of `fun`, a function of a vector (or matrix) that returns a scalar. `fval` is the value there, `exitflag` is 1 on success, and `grad` and `hessian` are the gradient and the quasi-Newton Hessian estimate at `x`.

Evans uses BFGS (MATLAB's default `'quasi-newton'`). With `'SpecifyObjectiveGradient', true`, `fun` returns the gradient as its second output and no finite differences are taken.

## Example

```matlab
rosen = @(x) 100*(x(2) - x(1)^2)^2 + (1 - x(1))^2;
[x, fval] = fminunc(rosen, [-1 2], optimoptions('fminunc', 'Display', 'off'))
```

## See also

[fmincon](fmincon) · [fsolve](fsolve) · [optimoptions](optimoptions)
