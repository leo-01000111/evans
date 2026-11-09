# gcf

Get the current figure.

## Syntax

    f = gcf

## Description

`gcf` returns the number of the current figure, the one the next plot command draws on. If no figure exists, it returns the number the first one will get. Pass the result to [saveas](saveas), [exportgraphics](exportgraphics) or [print](print) to name the figure to write.

## Example

```matlab
plot(1:5)
f = gcf
saveas(f, 'ramp.png')
```

## See also

[figure](figure) · [saveas](saveas) · [clf](clf) · [close](close)
