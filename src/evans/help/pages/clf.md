# clf

Clear the current figure.

## Syntax

    clf

## Description

`clf` empties the current figure: its plots, labels and any [subplot](subplot) grid. The figure keeps its number and its tab, and the next plot draws into it. Use [close](close) to remove the figure itself.

## Example

```matlab
plot(1:3)
clf
plot([3 2 1])
```

## See also

[figure](figure) · [close](close) · [gcf](gcf) · [hold](hold)
