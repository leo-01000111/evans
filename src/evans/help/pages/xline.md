# xline

Draw a vertical line across the axes at a given x.

## Syntax

    xline(x)
    xline(x, linespec)
    xline(x, linespec, label)
    xline(..., Name, Value)

## Description

`xline(x)` draws a vertical line from the bottom of the axes to the top at `x`; it stays full height when you zoom. `x` can be a vector, for one line at each value. [yline](yline) draws horizontal lines the same way.

`linespec` sets the line style and colour, as for [plot](plot): `xline(2, '--r')`. `label` writes text along the line; a cell array gives each line its own. `'Color'`, `'LineStyle'`, `'LineWidth'` and `'Label'` are used.

Like [text](text), it adds to the current axes without needing [hold](hold). Hovering the line shows its label.

## Example

```matlab
G = tf(1, [1 0.6 1]);
step(G); xline(5.5, '--', 'settled'); yline(1, ':')
```

## See also

[yline](yline) · [text](text) · [plot](plot)
