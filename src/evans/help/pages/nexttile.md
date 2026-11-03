# nexttile

Make the next tile of a tiled layout the current axes.

## Syntax

    nexttile
    nexttile(k)
    nexttile(span)
    nexttile(k, span)
    ax = nexttile(...)

## Description

`nexttile` moves to the next empty tile of the current [tiledlayout](tiledlayout), so that the next plot command draws there. Tiles are numbered along the rows, as [subplot](subplot) numbers its cells. Without a layout, `nexttile` starts a `'flow'` one.

`nexttile(k)` goes to tile `k`, making it current again if it already has a plot. `nexttile([r c])` makes the new axes span `r` rows and `c` columns of tiles; it goes in the first place where it fits.

`ax = nexttile` returns the axes. Passing `ax` first to [plot](plot), [title](title), [xlabel](xlabel) or the other plot functions makes them draw on that tile, whichever is current.

## Example

```matlab
tiledlayout(1, 2)
ax1 = nexttile; ax2 = nexttile;
plot(ax2, 1:5, (1:5).^2); title(ax2, 'square')
plot(ax1, 1:5, sqrt(1:5)); title(ax1, 'root')
```

## See also

[tiledlayout](tiledlayout) · [subplot](subplot) · [title](title)
