# pchip

Shape-preserving piecewise cubic interpolation.

## Syntax

    yq = pchip(x, y, xq)
    pp = pchip(x, y)

## Description

`pchip` passes a cubic through each interval whose slopes keep the data's shape: it does not overshoot, and it is monotone wherever the data are. That makes it the choice for measured curves where a [spline](spline) would ring. With two arguments it returns the piecewise polynomial for [ppval](ppval).

## Example

```matlab
x = 0:5;  y = [0 0 1 1 0 0];
yq = pchip(x, y, 0:0.5:5)
```

## See also

[spline](spline) · [ppval](ppval) · [interp2](interp2)
