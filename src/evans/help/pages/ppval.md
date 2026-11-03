# ppval

Evaluate a piecewise polynomial.

## Syntax

    v = ppval(pp, xq)

## Description

`pp` is the structure [spline](spline) or [pchip](pchip) returns with two arguments: its `breaks`, `coefs`, `order` and `dim`. Outside the breaks the end pieces are extended.

## Example

```matlab
pp = spline(0:3, [0 1 0 1]);
ppval(pp, [0.5 1.5 2.5])
```

## See also

[spline](spline) · [pchip](pchip)
