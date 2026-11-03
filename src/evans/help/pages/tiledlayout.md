# tiledlayout

Divide a figure into a grid of tiles for nexttile to fill.

## Syntax

    tiledlayout(m, n)
    tiledlayout('flow')
    tiledlayout('horizontal')
    tiledlayout('vertical')
    t = tiledlayout(...)

## Description

`tiledlayout(m, n)` starts a new figure laid out as `m` rows by `n` columns of tiles. Each call to [nexttile](nexttile) then makes the next tile the current axes, so the plot command after it draws there. It is MATLAB's newer alternative to [subplot](subplot).

`tiledlayout('flow')` starts with one tile and rearranges the grid as tiles are added, so that it stays close to square. `'horizontal'` lines the tiles up in one row and `'vertical'` in one column.

`t = tiledlayout(...)` returns the layout. `title(t, text)` puts a title over the whole layout, and `xlabel(t, text)` and `ylabel(t, text)` label it as a whole. Name-value pairs such as `'TileSpacing', 'compact'` are accepted and ignored.

## Example

```matlab
t = tiledlayout(2, 2);
nexttile; plot(rand(1, 10))
nexttile; bar([3 1 2])
nexttile([1 2]); stairs(1:5)
title(t, 'Three views')
```

## See also

[nexttile](nexttile) · [subplot](subplot) · [figure](figure)
