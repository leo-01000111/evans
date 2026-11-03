# quadgk

Integrate a function numerically by adaptive Gauss–Kronrod.

## Syntax

    q = quadgk(fun, a, b)
    q = quadgk(fun, a, b, Name, Value)
    [q, errbnd] = quadgk(...)

## Description

`quadgk` integrates `fun` from `a` to `b`, either of which may be infinite. `fun` must accept a vector and return a vector of the same size. `errbnd` estimates the absolute error.

The options are `'AbsTol'`, `'RelTol'`, `'Waypoints'` (points the subdivision must include, such as a kink) and `'MaxIntervalCount'`.

## Example

```matlab
q = quadgk(@(x) exp(-x.^2), -Inf, Inf)
sqrt(pi)
```

## See also

[integral](integral) · [integral2](integral2)
