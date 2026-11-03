# patch

Add filled polygons to the current axes.

## Syntax

    patch(x, y, c)
    patch(x, y, z, c)
    patch('XData', x, 'YData', y, Name, Value)
    patch('Faces', F, 'Vertices', V, Name, Value)

## Description

`patch(x, y, c)` draws the same filled polygons as [fill](fill), but always adds them to the current axes, as MATLAB's `patch` does, without needing [hold](hold). It is the usual way to shade a region behind a plot.

The polygon can also be given by name-value pairs: `'XData'` and `'YData'`, or `'Faces'` and `'Vertices'`, where each row of `F` lists the rows of `V` that make one face (NaN pads shorter faces). Vertices with three columns, or the `patch(x, y, z, c)` form, make a polygon in 3-D.

`'FaceColor'`, `'EdgeColor'`, `'FaceAlpha'` and `'LineWidth'` are used.

## Example

```matlab
t = linspace(0, 10, 200);
plot(t, sin(t))
patch([2 4 4 2], [-1 -1 1 1], 'g', 'FaceAlpha', 0.2, 'EdgeColor', 'none')
```

## See also

[fill](fill) · [area](area) · [plot](plot)
