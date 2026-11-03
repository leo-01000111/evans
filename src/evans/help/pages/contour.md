# contour

Draw contour lines of a matrix.

## Syntax

    contour(Z)
    contour(X, Y, Z)
    contour(..., n)
    contour(..., levels)
    contour(..., linespec)
    contour(..., 'ShowText', 'on')
    C = contour(...)

## Description

`contour(X, Y, Z)` draws the lines along which `Z` has the same value, as a map shows heights. `X` and `Y` are the grid, as for [surf](surf); `contour(Z)` uses the column and row numbers.

Without a count, round levels are chosen across the range of `Z`. `contour(..., n)` draws `n` levels evenly spaced within the range, and `contour(..., levels)` draws those values; to draw the single level `v`, give `[v v]`. `'LevelList'` sets the levels too.

The lines are coloured by level through the [colormap](colormap), unless `linespec` gives a colour. `'ShowText', 'on'` writes each level's value on its line. Hovering a line reads out its level.

`C = contour(...)` returns MATLAB's contour matrix: for each line, a column of the level and the number of points, then the points' x and y as columns.

## Example

```matlab
[X, Y] = meshgrid(-3:0.1:3);
Z = X.^2 + 3*Y.^2;
contour(X, Y, Z, [1 4 9 16], 'ShowText', 'on'); axis equal
```

## See also

[contourf](contourf) · [surf](surf) · [meshgrid](meshgrid) · [quiver](quiver)
