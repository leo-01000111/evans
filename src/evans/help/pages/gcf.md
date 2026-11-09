# gcf

The number of the current figure.

## Syntax

    n = gcf

## Description

`gcf` returns the number of the current figure: the one [figure](figure)`(n)` last selected, the one the last plot drew into, or the tab you selected in the figure area. When no figure is open it returns the number the next one would get.

Evans has no graphics handles, so `gcf` is a plain number, which is what [exportgraphics](exportgraphics) and `saveas` take.

## Example

```matlab
plot(1:3)
plot(1:4)
figure(1)
n = gcf
```

## See also

[figure](figure) · [close](close) · [clf](clf)
