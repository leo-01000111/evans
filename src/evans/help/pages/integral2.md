# integral2

Integrate a function of two variables over a region.

## Syntax

    q = integral2(fun, xmin, xmax, ymin, ymax)
    q = integral2(fun, xmin, xmax, ymin, ymax, Name, Value)

## Description

`fun(x, y)` must accept arrays and work elementwise. The region is `xmin ≤ x ≤ xmax` and `ymin ≤ y ≤ ymax`, where `ymin` and `ymax` may be functions of `x` for a region that is not a rectangle.

Evans integrates in y for each x and then in x (MATLAB's `'iterated'` method). The options are `'AbsTol'`, `'RelTol'` and `'Method'`.

## Example

```matlab
q = integral2(@(x, y) x.*y, 0, 1, 0, 2)
halfdisc = integral2(@(x, y) ones(size(x)), -1, 1, 0, @(x) sqrt(1 - x.^2))
```

## See also

[integral](integral) · [quadgk](quadgk)
