# close

Close figures.

## Syntax

    close
    close all

## Description

`close` closes the figures. In Evans the call closes every figure, whichever argument it has, so `close`, `close all` and `close(f)` all leave the figure area empty; the next plot opens a new figure.

To empty one figure and keep its window, use [clf](clf). `close` does not touch the workspace, which [clear](clear) handles.

## Example

```matlab
plot(1:5)
close all
plot(5:-1:1)
```

## See also

[clf](clf) · [figure](figure) · [clear](clear) · [gcf](gcf)
