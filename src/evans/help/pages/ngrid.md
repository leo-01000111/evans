# ngrid

Draw the Nichols chart grid: contours of constant closed-loop gain and phase.

## Syntax

    ngrid
    ngrid('new')

## Description

`ngrid` superimposes the Nichols chart grid on the current axes, normally right after [nichols](nichols). For each point of an open-loop response `L` the grid reads off the closed loop `T = L/(1+L)`, assuming unity negative feedback: contours of constant `|T|` labelled in dB (6, 3, 1, 0.5, 0.25, 0, -1, -3, -6, -12, -20 and -40 dB), and contours of constant `arg T` labelled in degrees (-1 to -150°). The pattern repeats every 360° to cover whatever phase the curve spans.

The highest gain contour the curve touches is the closed-loop resonant peak, and where the curve crosses the -3 dB contour is close to the closed-loop bandwidth.

`ngrid('new')` starts fresh axes with the grid and holds them, so the [nichols](nichols) call that follows draws on top. `ngrid` is the same as `grid on` on a Nichols chart.

## Example

```matlab
L = tf(20, [1 6 5 0]);
nichols(L)
ngrid
```

## See also

[nichols](nichols) · [grid](grid) · [nyquist](nyquist) · [margin](margin)
