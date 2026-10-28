# pwelch

Power spectral density by Welch's averaged periodogram.

## Syntax

    [pxx, w] = pwelch(x)
    [pxx, w] = pwelch(x, window, noverlap, nfft)
    [pxx, f] = pwelch(x, window, noverlap, nfft, fs)

## Description

MATLAB's defaults: eight segments overlapping by half, a Hamming window, and `nfft = max(256, 2^nextpow2(segment length))`. For real data the estimate is one-sided, with columns `pxx` and `w` (rad/sample) or `f` (Hz when `fs` is given). `[]` leaves an argument at its default.

## Example

```matlab
fs = 1000;
t = 0:1/fs:1;
x = sin(2*pi*100*t) + randn(size(t));
[pxx, f] = pwelch(x, [], [], [], fs);
[~, k] = max(pxx);
f(k)
```

## See also


