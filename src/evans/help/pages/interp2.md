# interp2

Interpolate data on a 2-D grid.

## Syntax

    Vq = interp2(X, Y, V, Xq, Yq)
    Vq = interp2(V, Xq, Yq)
    Vq = interp2(..., method)
    Vq = interp2(..., method, extrapval)

## Description

`V` holds values on a grid: `X` and `Y` are its coordinates, as vectors or as the matrices `meshgrid` makes; without them, column and row numbers are used. `Xq` and `Yq` are the points to interpolate at.

`method` is `'linear'` (the default), `'nearest'` or `'spline'`. Points outside the grid are NaN unless `extrapval` gives another value.

## Example

```matlab
V = [1 2; 3 4];
interp2([1 2], [1 2], V, 1.5, 1.5)
interp2(V, 3, 1, 'linear', 0)
```

## See also

[griddata](griddata) · [spline](spline) · [pchip](pchip)
