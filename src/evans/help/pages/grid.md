# grid

Turn grid lines on the current axes on or off.

## Syntax

    grid on
    grid off
    grid minor
    grid(state)

## Description

Evans draws grid lines on every plot already, so on most plots `grid on` changes nothing you can see. It is accepted so that MATLAB scripts which call it run unchanged.

The exceptions are the control charts, where `grid on` means what it does in MATLAB: on a [nyquist](nyquist) diagram it draws the M-circles of constant closed-loop gain, and on a [nichols](nichols) chart the closed-loop gain and phase contours (the same as [ngrid](ngrid)).

`grid off` and `grid minor` are accepted as well, and are recorded on the figure, but the figure window does not act on them yet: the grid stays as it is. Unlike MATLAB, `grid` with no argument does not toggle; it behaves like `grid on`.

`grid` applies to the current axes, so it comes after the plot command: on the same line, later in the script, or at a later prompt.

## Example

```matlab
t = 0:0.05:5;
plot(t, exp(-t).*cos(4*t)); grid on
```

## See also

[plot](plot) · [axis](axis) · [title](title) · [hold](hold)
