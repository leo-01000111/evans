# surf

Draw a shaded surface over a grid.

## Syntax

    surf(Z)
    surf(X, Y, Z)
    surf(X, Y, Z, C)
    surf(..., Name, Value)
    surfc(...)

## Description

`surf(X, Y, Z)` draws the surface of heights `Z` over the grid `X`, `Y`, usually made with [meshgrid](meshgrid). `X` and `Y` can also be vectors, with `length(X)` the number of columns of `Z` and `length(Y)` the number of rows. `surf(Z)` uses the column and row numbers.

The faces are coloured by height through the [colormap](colormap); `C`, a matrix the size of `Z`, colours them by its values instead. [colorbar](colorbar) shows the scale and [caxis](caxis) fixes its range. The grid lines are drawn in black; [shading](shading) `flat` or `interp` takes them off, as does `'EdgeColor', 'none'`. `'FaceColor'` with a colour paints the whole surface in it, and `'FaceAlpha'` makes it see-through.

`surfc` draws a contour plot below the surface as well. Drag to turn the axes; [view](view) sets the angle.

## Example

```matlab
[X, Y] = meshgrid(-2:0.2:2);
surf(X, Y, X.*exp(-X.^2 - Y.^2)); colorbar
```

## See also

[mesh](mesh) · [meshgrid](meshgrid) · [contour](contour) · [shading](shading) · [view](view) · [colormap](colormap)
