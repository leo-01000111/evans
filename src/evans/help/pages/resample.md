# resample

Change the sample rate by a rational factor p/q.

## Syntax

    y = resample(x, p, q)
    y = resample(x, p, q, n)
    y = resample(x, p, q, n, beta)

## Description

`resample` upsamples by `p`, filters with a lowpass FIR filter and downsamples by `q`, so `y` has `ceil(length(x)*p/q)` samples. The filter is MATLAB's: least-squares design times a Kaiser window (`beta = 5`), `2*n*max(p, q) + 1` taps long (`n = 10`).

Evans takes integer factors only, not sample times, and not your own filter coefficients.

## Example

```matlab
t = 0:0.1:1;
x = sin(2*pi*t);
y = resample(x, 3, 2);
length(y)
```

## See also

[filtfilt](filtfilt)
