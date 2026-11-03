# fill

Draw filled polygons.

## Syntax

    fill(x, y, c)
    fill(x1, y1, c1, x2, y2, c2, ...)
    fill(..., Name, Value)

## Description

`fill(x, y, c)` draws the polygon whose corners are `(x(i), y(i))`, closing it back to the first corner, and fills it with colour `c`. `c` is a colour letter or name, a hex code, an RGB triplet, or a number taken through the [colormap](colormap).

When `x` and `y` are matrices, each column is one polygon. Several `x, y, c` groups in one call draw several polygons.

Like [plot](plot), `fill` replaces what the axes showed unless [hold](hold) is on; [patch](patch) always adds. The edge is drawn in black; `'EdgeColor', 'none'` leaves it off and `'FaceAlpha'` makes the fill see-through.

## Example

```matlab
t = linspace(0, 2*pi, 7);
fill(cos(t), sin(t), 'y'); axis equal
```

## See also

[patch](patch) · [area](area) · [plot](plot)
