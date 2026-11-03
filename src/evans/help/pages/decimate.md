# decimate

Lower a signal's sample rate after low-pass filtering it.

## Syntax

    y = decimate(x, r)
    y = decimate(x, r, n)

## Description

`decimate` keeps every `r`-th sample after a zero-phase 8th-order Chebyshev type I low-pass filter (order `n` if given) removes what would alias. `r` is a positive integer; for a large one, decimate in stages.

Evans does not support the `'fir'` option.

## Example

```matlab
t = (0:99)/100;  x = sin(2*pi*3*t);
y = decimate(x, 4);
numel(y)
```

## See also

[resample](resample) · [filtfilt](filtfilt)
