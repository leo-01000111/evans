# text

Write text at a point on the axes.

## Syntax

    text(x, y, txt)
    text(x, y, z, txt)
    text(..., Name, Value)

## Description

`text(x, y, txt)` writes `txt` on the current axes with its left edge at `(x, y)`, in the axes' own units, so it moves with the data when you zoom. `x` and `y` can be vectors with a cell array of strings, one per point. With a `z` coordinate the text is placed in 3-D.

`text` never replaces the plot: it is added to the current axes whether or not [hold](hold) is on.

`'HorizontalAlignment'` (`'left'`, `'center'`, `'right'`), `'VerticalAlignment'` (`'middle'`, `'top'`, `'bottom'`), `'Color'`, `'FontSize'`, `'FontWeight'`, `'Rotation'` and `'BackgroundColor'` are used.

## Example

```matlab
t = linspace(0, 10, 200);
plot(t, exp(-t/3).*sin(2*t))
text(1.2, 0.75, 'first peak', 'Color', 'r')
```

## See also

[annotation](annotation) · [xline](xline) · [title](title)
