# periodogram

Power spectral density estimate from one window of data.

## Syntax

    pxx = periodogram(x)
    pxx = periodogram(x, window, nfft)
    [pxx, f] = periodogram(x, window, nfft, fs)
    periodogram(...)

## Description

The periodogram is the squared magnitude of the (windowed) FFT of the whole record, scaled to a density. `window` is a vector as long as `x` or `[]` for a rectangular one; `nfft` defaults to the next power of two of at least 256. With `fs`, `f` is in Hz and the density per Hz; otherwise rad/sample.

A real signal gives the one-sided spectrum; `'twosided'` and `'centered'` give the others, and `'power'` the power spectrum instead of the density. With no outputs it plots in dB. [pwelch](pwelch) averages overlapping segments for a smoother estimate.

## Example

```matlab
fs = 100;  t = (0:199)'/fs;
x = sin(2*pi*10*t);
[p, f] = periodogram(x, [], 256, fs);
[~, k] = max(p);  f(k)
```

## See also

[pwelch](pwelch) · [spectrogram](spectrogram) · [hann](hann)
