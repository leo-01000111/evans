# fsolve

Solve a system of nonlinear equations F(x) = 0.

## Syntax

    x = fsolve(fun, x0)
    x = fsolve(fun, x0, options)
    [x, fval, exitflag, output] = fsolve(...)

## Description

`fsolve` starts from `x0` and finds `x` with `fun(x)` zero. A square system uses a dogleg trust-region method, as MATLAB's default does; others use Levenberg-Marquardt. `exitflag` is positive when the equations were solved, and not positive (with a message) when they were not, so check it rather than trusting `x`.

## Example

```matlab
f = @(x) [x(1)^2 + x(2)^2 - 4; x(1) - x(2)];
[x, fval, exitflag] = fsolve(f, [1; 1])
```

## See also


