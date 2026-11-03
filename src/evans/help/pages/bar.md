# bar

Draw a bar chart; a matrix's columns side by side or stacked.

## Syntax

    bar(y)
    bar(x, y)
    bar(x, y, width)
    bar(..., 'stacked')
    bar(..., color)
    barh(...)

## Description

`bar(y)` draws one bar for each element of `y`, at 1, 2, 3 and so on; `bar(x, y)` puts them at the values of `x`. `width` is the fraction of the space between bars each one fills, 0.8 by default.

When `y` is a matrix, each row is a group and each column a series: the bars of a group stand side by side, or on top of each other with `'stacked'`. Each series takes the next colour of the colour order; a colour letter or `'FaceColor'` colours them all.

`barh` takes the same arguments and draws the bars horizontally.

## Example

```matlab
bar([2 3; 4 1; 3 3], 'stacked'); legend('first', 'second')
```

## See also

[area](area) · [errorbar](errorbar) · [pie](pie)
