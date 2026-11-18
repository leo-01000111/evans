# freqresp

Frequency response of a model at the frequencies you give, as complex numbers.

## Syntax

    H = freqresp(sys, w)

## Description

`H = freqresp(sys, w)` evaluates the transfer function of `sys` at `s = jw` for each frequency in `w`, in rad/s. For a discrete model with sample time `Ts` the point is on the unit circle, `z = exp(j*w*Ts)`. `H` is an `ny`-by-`nu`-by-`N` array of complex values, one page per frequency, so a single-input single-output model gives 1-by-1-by-`N`: `squeeze(H)` makes it a vector (a column), and `abs(H)` is the gain and `angle(H)` the phase in radians. `sys` can be a `tf`, `zpk` or `ss` model.

The frequencies must be given. Evans returns one output; MATLAB can also return the frequency vector as a second output, which is not supported here. For one complex point, use [evalfr](evalfr); for magnitude and phase over a sweep, [bode](bode) with output arguments.

## Example

```matlab
G = tf(10, [1 2 10]);
w = logspace(-1, 2, 5);
H = freqresp(G, w);
mag_dB = 20*log10(abs(squeeze(H)))
```

## See also

[evalfr](evalfr) · [bode](bode) · [nyquist](nyquist) · [logspace](logspace)
