# plot

Line plot of data: one or more y vectors against x, on linear axes.

## Syntax

    plot(y)
    plot(x, y)
    plot(x, y, spec)
    plot(x1, y1, spec1, x2, y2, spec2, ...)

## Description

`plot(x, y)` draws `y` against `x`. The two must have the same number of elements. If `y` is a matrix, each column is drawn as its own line against `x` (or each row, when the rows match the length of `x`).

`plot(y)` draws `y` against its index, `1:length(y)`. A complex `y` on its own is drawn as its imaginary part against its real part. When `x` and `y` are both given and one of them is complex, the imaginary parts are dropped with a warning.

`spec` is a MATLAB line specification such as `'--'`, `'r:'` or `'o-'`: a line style (`-`, `--`, `:`, `-.`), a colour letter (`r g b c m y k w`) and a marker (`o + * . x s d ^ v < > p h`), in any order and each optional. A marker with no line style draws unconnected points. Without a colour, lines take the theme's colours in turn, or those [colororder](colororder) set. The name-value pairs `'Color'`, `'LineWidth'`, `'LineStyle'`, `'Marker'`, `'MarkerSize'`, `'MarkerFaceColor'`, `'MarkerEdgeColor'` and `'DisplayName'` are used; others are accepted and ignored. A first argument from [nexttile](nexttile) or `gca` says which axes to draw on.

Several `x, y` pairs in one call draw several lines on the same axes. Without [hold](hold), each `plot` starts a fresh figure.

At the console, a figure is drawn when the command you entered finishes. [title](title), [legend](legend), [hold](hold) and the other annotations typed at a later prompt reach the figure drawn last, which is redrawn in place, as in MATLAB. Once that figure is closed, the next plot starts afresh.

Hover over a curve to read its values, and click to pin a data tip there; click the tip again to remove it. Right-click offers *Remove data tips* and the export formats.

For a logarithmic frequency axis use [semilogx](semilogx). To plot a model's response, call [step](step) or [bode](bode) directly; `[y, t] = step(G)` followed by `plot(t, y)` gives the same curve when you need to combine it with other data.

## Example

```matlab
t = linspace(0, 10, 200);
y1 = 1 - exp(-t);
y2 = 1 - exp(-0.5*t);
plot(t, y1, t, y2, '--'); legend('tau = 1', 'tau = 2'); xlabel('t (s)')
```

## See also

[semilogx](semilogx) · [hold](hold) · [figure](figure) · [subplot](subplot) · [legend](legend) · [scatter](scatter) · [plot3](plot3) · [step](step)
