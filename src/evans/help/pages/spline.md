# spline

Cubic spline interpolation, MATLAB's not-a-knot spline.

## Syntax

    yq = spline(x, y, xq)
    pp = spline(x, y)

## Description

`spline(x, y, xq)` evaluates the not-a-knot cubic spline through the points at `xq`. When `y` has two more values than `x`, the first and last are the slopes at the ends (a clamped spline). With two points the spline is a straight line, with three a parabola. `pp = spline(x, y)` returns the piecewise polynomial for `ppval`.

## Example

```matlab
x = 0:4;
y = x.^3;
spline(x, y, 2.5)
```

## See also


