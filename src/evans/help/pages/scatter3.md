# scatter3

Draw points as markers in 3-D.

## Syntax

    scatter3(x, y, z)
    scatter3(x, y, z, sz, c)
    scatter3(..., 'filled')

## Description

`scatter3(x, y, z)` puts a marker at each point `(x(i), y(i), z(i))`. The size, colour, marker and `'filled'` arguments are those of [scatter](scatter); a colour vector colours each point through the [colormap](colormap).

## Example

```matlab
z = linspace(0, 1, 60);
scatter3(z.*cos(12*z), z.*sin(12*z), z, 40, z, 'filled')
```

## See also

[scatter](scatter) · [plot3](plot3) · [view](view)
