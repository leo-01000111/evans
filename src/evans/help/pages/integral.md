# integral

Numerical integration of a function over an interval.

## Syntax

    q = integral(fun, a, b)
    q = integral(fun, a, b, Name, Value)

## Description

`integral` integrates `fun` from `a` to `b` by adaptive quadrature; either limit may be `Inf` or `-Inf`. As in MATLAB, `fun` is called with a vector of points and must return a vector of the same size, so write `@(x) x.^2`, not `@(x) x^2`. `'ArrayValued', true` integrates a function that returns an array for a scalar `x`. `'AbsTol'`, `'RelTol'` and `'Waypoints'` are supported.

## Example

```matlab
q = integral(@(x) exp(-x.^2), -Inf, Inf)
sqrt(pi)
```

## See also

[int](int)
