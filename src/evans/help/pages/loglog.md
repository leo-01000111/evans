# loglog

Line plot with logarithmic x and y axes.

## Syntax

    loglog(y)
    loglog(x, y)
    loglog(x, y, spec)
    loglog(x1, y1, spec1, x2, y2, spec2, ...)

## Description

`loglog` takes the same arguments as [plot](plot) and draws the same curves, with both axes on a log scale. A power law `y = c*x^p` becomes a straight line of slope `p`, which makes the plot useful for a magnitude response against frequency in absolute units, or a cost against problem size.

Points where `x` or `y` is less than or equal to zero cannot be shown on a log axis and are left out of the drawing. With [hold](hold) on, several `loglog` calls share the axes.

## Example

```matlab
w = logspace(-1, 2, 200);
G = tf(1, [1 1]);
loglog(w, abs(freqresp(G, w))); xlabel('w (rad/s)'); ylabel('|G|')
```

## See also

[semilogx](semilogx) · [semilogy](semilogy) · [plot](plot) · [bode](bode)
