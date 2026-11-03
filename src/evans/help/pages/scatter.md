# scatter

Draw points as markers, each with its own size and colour if you like.

## Syntax

    scatter(x, y)
    scatter(x, y, sz)
    scatter(x, y, sz, c)
    scatter(..., marker)
    scatter(..., 'filled')
    scatter(..., Name, Value)

## Description

`scatter(x, y)` puts a circle at each point `(x(i), y(i))`, with no line between them. `x` and `y` are vectors with the same number of elements.

`sz` is the marker area in points squared, as in MATLAB: one number for every marker, or one per point. The default is 36. Pass `[]` to keep the default while giving a colour.

`c` sets the colour. A colour letter or name (`'r'`, `'red'`), a hex code or an RGB triplet colours every marker the same. A vector with one value per point colours each marker through the [colormap](colormap), and [colorbar](colorbar) shows the scale. An n-by-3 matrix gives each point its own RGB colour.

`marker` is a marker letter such as `'s'`, `'d'`, `'^'` or `'x'`. `'filled'` fills the markers instead of drawing their outline. The name-value pairs `'MarkerEdgeColor'`, `'MarkerFaceColor'`, `'LineWidth'` and `'DisplayName'` are used; others are accepted and ignored.

Hover over a marker to read its coordinates, and click it to pin a data tip.

## Example

```matlab
x = linspace(0, 2*pi, 40);
scatter(x, sin(x), 30 + 60*abs(cos(x)), cos(x), 'filled'); colorbar
```

## See also

[plot](plot) · [scatter3](scatter3) · [colormap](colormap) · [colorbar](colorbar)
