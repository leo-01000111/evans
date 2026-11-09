# meshgrid

Make the grid of points a surface or a contour plot is drawn over.

## Syntax

    [X, Y] = meshgrid(x, y)
    [X, Y] = meshgrid(x)
    [X, Y, Z] = meshgrid(x, y, z)

## Description

`[X, Y] = meshgrid(x, y)` returns two matrices with `length(y)` rows and `length(x)` columns: each row of `X` is `x`, and each column of `Y` is `y`. Evaluating a function element-wise on `X` and `Y` then gives its values over the whole grid, ready for [surf](surf), [contour](contour) or [quiver](quiver). `meshgrid(x)` is `meshgrid(x, x)`.

`[X, Y, Z] = meshgrid(x, y, z)` makes three-dimensional grids of size `length(y)`-by-`length(x)`-by-`length(z)`. See [ndgrid](ndgrid) for the variant with the first input down the rows.

## Example

```matlab
[X, Y] = meshgrid(1:3, 10:10:20)
```

## See also

[surf](surf) · [contour](contour) · [quiver](quiver)
