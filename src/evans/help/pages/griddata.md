# griddata

Interpolate scattered data onto points or a grid.

## Syntax

    vq = griddata(x, y, v, xq, yq)
    vq = griddata(x, y, v, xq, yq, method)

## Description

`x`, `y` and `v` are scattered samples. `griddata` triangulates them (Delaunay) and interpolates at `xq`, `yq`. `method` is `'linear'` (the default) or `'nearest'`. Outside the samples' convex hull the result is NaN, as in MATLAB. Repeated points are averaged, with a warning.

## Example

```matlab
x = [0 1 0 1 0.5];  y = [0 0 1 1 0.5];  v = x + y;
vq = griddata(x, y, v, 0.25, 0.75)
```

## See also

[interp2](interp2) · [fit](fit)
