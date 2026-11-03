# meshgrid

Make the grid of points a surface or a contour plot is drawn over.

## Syntax

    [X, Y] = meshgrid(x, y)
    [X, Y] = meshgrid(x)

## Description

`[X, Y] = meshgrid(x, y)` returns two matrices with `length(y)` rows and `length(x)` columns: each row of `X` is `x`, and each column of `Y` is `y`. Evaluating a function element-wise on `X` and `Y` then gives its values over the whole grid, ready for [surf](surf), [contour](contour) or [quiver](quiver). `meshgrid(x)` is `meshgrid(x, x)`.

Three-dimensional grids, `meshgrid(x, y, z)`, need N-D arrays, which Evans does not have yet.

## Example

```matlab
[X, Y] = meshgrid(1:3, 10:10:20)
```

## See also

[surf](surf) · [contour](contour) · [quiver](quiver)
