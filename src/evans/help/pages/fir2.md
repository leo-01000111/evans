# fir2

Design an FIR filter for an arbitrary magnitude response.

## Syntax

    b = fir2(n, f, m)
    b = fir2(n, f, m, npt)
    b = fir2(n, f, m, npt, lap)
    b = fir2(..., window)

## Description

`fir2` designs an order-`n` FIR filter whose magnitude follows `m` at the frequencies `f`. `f` runs from 0 to 1, where 1 is the Nyquist frequency, and is non-decreasing (a repeated frequency makes a step). The response is sampled on `npt` points (512 by default), with jumps smoothed over `lap` points, then windowed (Hamming by default).

An odd `n` needs zero gain at Nyquist, as in MATLAB. Evans does not support the `'h'` and `'d'` filter types.

## Example

```matlab
b = fir2(20, [0 0.3 0.4 1], [1 1 0 0]);
[h, w] = freqz(b, 1, 4);
abs(h)'
```

## See also

[fir1](fir1) · [designfilt](designfilt)
