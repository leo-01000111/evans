# plot3

Draw lines through points in 3-D.

## Syntax

    plot3(x, y, z)
    plot3(x, y, z, linespec)
    plot3(x1, y1, z1, ..., xn, yn, zn)
    plot3(..., Name, Value)

## Description

`plot3(x, y, z)` draws a line through the points `(x(i), y(i), z(i))` on 3-D axes. When the inputs are matrices, each column is one line. Several `x, y, z` groups draw several lines.

`linespec` works as for [plot](plot): `'o'` draws only markers, `'r--'` a dashed red line.

3-D axes are drawn by matplotlib inside the figure: drag with the mouse to turn them, right-drag to zoom. [view](view) sets the viewing angle from a script, and [zlabel](zlabel) labels the third axis.

## Example

```matlab
t = linspace(0, 6*pi, 400);
plot3(cos(t), sin(t), t/(2*pi)); zlabel('turns')
```

## See also

[plot](plot) · [scatter3](scatter3) · [view](view) · [zlabel](zlabel)
