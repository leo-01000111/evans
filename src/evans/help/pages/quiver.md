# quiver

Draw a field of arrows.

## Syntax

    quiver(X, Y, U, V)
    quiver(U, V)
    quiver(..., scale)
    quiver(..., 'off')
    quiver(..., linespec)

## Description

`quiver(X, Y, U, V)` draws an arrow at each point `(X(i), Y(i))` pointing along `(U(i), V(i))`: a velocity field, a gradient, or a phase portrait. `X` and `Y` are usually a [meshgrid](meshgrid); `quiver(U, V)` places the arrows on the column and row numbers.

The arrows are scaled automatically, as in MATLAB, so that the longest fits in the grid spacing without overlapping its neighbour. `scale` multiplies that length, and `0` or `'off'` draws the vectors at their true length. `linespec` sets the colour and line style.

[quiver3](quiver3) draws arrows in 3-D.

## Example

```matlab
[X, Y] = meshgrid(-2:0.4:2);
quiver(X, Y, Y, -X - 0.5*Y); axis equal; title('Damped oscillator')
```

## See also

[quiver3](quiver3) · [contour](contour) · [meshgrid](meshgrid)
