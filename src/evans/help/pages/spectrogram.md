# spectrogram

Short-time Fourier transform of a signal.

## Syntax

    s = spectrogram(x)
    s = spectrogram(x, window, noverlap, nfft)
    [s, f, t] = spectrogram(x, window, noverlap, nfft, fs)
    [s, f, t, ps] = spectrogram(...)

## Description

`spectrogram` cuts `x` into overlapping segments, windows each, and returns their FFTs as the columns of `s`, one per segment: the time–frequency picture of a signal whose content changes. `window` is a length or a vector (a Hamming window of an eighth of the signal by default), `noverlap` the overlap in samples (half a segment by default). `f` and `t` are the frequencies and the segment centres; `ps` is the power spectral density of each segment.

Evans cannot draw the spectrogram yet: ask for the outputs.

## Example

```matlab
fs = 1000;  t = (0:1999)/fs;
x = sin(2*pi*(50 + 100*t).*t);
[s, f, tt] = spectrogram(x, 256, 128, 256, fs);
size(s)
```

## See also

[pwelch](pwelch) · [periodogram](periodogram)
