# errorbar

Plot data with error bars at each point.

## Syntax

    errorbar(y, err)
    errorbar(x, y, err)
    errorbar(x, y, neg, pos)
    errorbar(x, y, yneg, ypos, xneg, xpos)
    errorbar(..., ornt)
    errorbar(..., linespec)

## Description

`errorbar(x, y, err)` draws `y` against `x` and a vertical bar at each point reaching `err(i)` above and below it. `errorbar(y, err)` uses `1:length(y)` for `x`. `err` can be one number for every point.

`errorbar(x, y, neg, pos)` makes the bars uneven: `neg(i)` below the point and `pos(i)` above it. With six inputs the last two are the horizontal bars' lengths to the left and right.

`ornt` is `'vertical'` (the default), `'horizontal'` or `'both'`; it says which way the bars of the three- and four-input forms go.

`linespec` sets the line, marker and colour as for [plot](plot): `'o'` draws the points as markers with no line between them.

## Example

```matlab
x = 1:8;
y = 2*x + randn(1, 8);
errorbar(x, y, 0.5 + 0.2*x, 'o'); title('Measurements')
```

## See also

[plot](plot) · [bar](bar) · [scatter](scatter)
