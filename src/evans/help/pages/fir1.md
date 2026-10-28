# fir1

Window-method FIR filter design.

## Syntax

    b = fir1(n, Wn)
    b = fir1(n, Wn, ftype)
    b = fir1(n, Wn, window)

## Description

`fir1` designs an order-`n` (length `n+1`) linear-phase FIR filter with cutoff `Wn` (1 is the Nyquist frequency), using a Hamming window, scaled to unit gain in the passband. `ftype` is `'low'` (the default), `'high'`, `'bandpass'` (the default for a two-element `Wn`) or `'stop'`; a window vector of length `n+1` replaces the Hamming window.

A high-pass or band-stop filter needs an even order; as in MATLAB, an odd one is raised by 1 with a warning.

## Example

```matlab
b = fir1(20, 0.3);
y = filter(b, 1, randn(1, 200));
```

## See also

[filtfilt](filtfilt)
