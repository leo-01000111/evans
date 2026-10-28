# hann

Hann (raised-cosine) window.

## Syntax

    w = hann(n)
    w = hann(n, 'symmetric')
    w = hann(n, 'periodic')

## Description

`hann(n)` is the column `0.5*(1 - cos(2*pi*(0:n-1)'/(n-1)))`, zero at both ends. `'periodic'` gives the window for spectral analysis, the first `n` points of a symmetric window of length `n+1`. `hanning` is MATLAB's older form without the zero ends.

## Example

```matlab
w = hann(8)
```

## See also

[pwelch](pwelch)
