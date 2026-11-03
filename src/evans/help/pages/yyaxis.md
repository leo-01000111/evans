# yyaxis

Plot against a second y axis on the right.

## Syntax

    yyaxis left
    yyaxis right

## Description

`yyaxis right` gives the current axes a second y axis on the right and makes it the active one: the plots that follow are scaled against it, and [ylabel](ylabel) and [ylim](ylim) set its label and limits. `yyaxis left` goes back to the left axis. It is the way to show two signals in different units, a speed and a current for example, against one time axis.

Everything on one side is drawn in that side's colour, the first of the colour order on the left and the second on the right, and each axis's ticks take that colour too, unless you give the curves colours of your own.

Without [hold](hold), a plot replaces only what was on the active side. The [legend](legend) lists the curves of both sides.

## Example

```matlab
t = linspace(0, 10, 200);
yyaxis left; plot(t, sin(t)); ylabel('position (m)')
yyaxis right; plot(t, 50*cos(t)); ylabel('speed (mm/s)')
```

## See also

[plot](plot) · [ylabel](ylabel) · [ylim](ylim) · [hold](hold)
