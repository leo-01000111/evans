# grpdelay

Group delay of a digital filter.

## Syntax

    gd = grpdelay(b, a)
    gd = grpdelay(b, a, n)
    [gd, w] = grpdelay(b, a, n)
    [gd, f] = grpdelay(b, a, n, fs)
    gd = grpdelay(d, n)
    grpdelay(...)

## Description

The group delay, in samples, at `n` frequencies (512 by default) from 0 up to Nyquist (`'whole'` for the full circle), or at the frequencies `n` itself lists. A linear-phase FIR filter of order N delays every frequency by N/2. `d` from [designfilt](designfilt) stands for `b, a`. With no outputs, a plot.

## Example

```matlab
gd = grpdelay(ones(1, 5)/5, 1, 4)'
```

## See also

[impz](impz) · [fir1](fir1)
