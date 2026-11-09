# ginput

Read points by clicking on the current figure.

## Syntax

    [x, y] = ginput(n)
    [x, y, button] = ginput(n)
    xy = ginput(n)

## Description

Waits for `n` clicks on the first plot of the figure on top, in its data coordinates; with no `n`, until Return is pressed. `button` is 1, 2 or 3 for the left, middle or right button. Headless, no points are returned.

## Example

```matlab
plot(1:5)
[x, y] = ginput(2);
numel(x)
```

## See also

[plot](plot) · [uigetfile](uigetfile)
