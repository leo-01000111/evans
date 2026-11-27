# fminsearch

Find a local minimum of a function of several variables without using derivatives.

## Syntax

    x = fminsearch(f, x0)
    x = fminsearch(f, x0, options)
    [x, fval, exitflag, output] = fminsearch(f, x0)

## Description

`f` is a function handle taking one argument of the same size as `x0` and returning a scalar. `x0` may be a scalar, a row or a column; `x` comes back with the same shape as `x0`. To pass extra parameters, capture them in the handle: `@(p) cost(p, data)`.

The search is the Nelder-Mead simplex method, started from the simplex of `x0` with 5% steps (0.00025 for components that are zero).

`options` comes from `optimset`. Evans reads `TolX` and `TolFun` (both default `1e-4`), `MaxIter` and `MaxFunEvals` (both default `200` times the number of variables). Other fields are ignored.

`fval` is `f(x)`. `exitflag` is `1` when the search stopped on its tolerances and `0` when it ran out of iterations or evaluations; with `MaxIter` set to 10 on the Rosenbrock function it was `0`. `output` is a struct with `iterations`, `funcCount` and `algorithm` (`'Nelder-Mead simplex direct search'`). Evans prints no message when the limit is reached; test `exitflag`.

The result is a local minimum, and the answer is only as accurate as the tolerances: a minimum at 3 prints as `3.0000`, so compare with a tolerance, not with `==`. The objective must return a real scalar: a vector stops with "The function must return a scalar value", and a value that is not a number stops with a Python-level message such as "could not convert string to float".

## Example

```matlab
rosen = @(p) 100*(p(2) - p(1)^2)^2 + (1 - p(1))^2;
[x, fval, flag, out] = fminsearch(rosen, [-1.2 1]);
x
flag
out.iterations
```

`x` is about `1.0000 1.0000`, `flag` is 1, and the search takes 85 iterations (159 evaluations of the function).

## See also

[fminunc](fminunc) · [fmincon](fmincon) · [fzero](fzero) · [lsqnonlin](lsqnonlin)
