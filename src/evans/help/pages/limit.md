# limit

Limit of a symbolic expression.

## Syntax

    L = limit(f, x, a)
    L = limit(f, a)
    L = limit(f)
    L = limit(f, x, a, 'left')
    L = limit(f, x, a, 'right')

## Description

`limit(f, x, a)` is the limit of `f` as `x` approaches `a`. Without `x` the variable is the one closest to `x` alphabetically, and without `a` the point is 0. `a` may be `Inf` or `-Inf`.

The limit is two-sided unless `'left'` or `'right'` is given. Where the two sides disagree it is `NaN`: `limit(1/x, x, 0)` is `NaN`, while from the right it is `Inf`.

The final value theorem is a limit: for a stable closed loop `T`, the steady-state step response is `limit(s*T/s, s, 0)`, and the initial value `limit(s*T/s, s, Inf)`.

## Example

```matlab
syms s x
limit(sin(x)/x, x, 0)
T = 5/(s^2 + 3*s + 2);
limit(s*T/s, s, 0)
```

## See also

[int](int) · [diff](diff) · [dcgain](dcgain) · [subs](subs)
