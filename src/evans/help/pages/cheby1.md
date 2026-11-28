# cheby1

Design a Chebyshev type I filter, with ripple in the passband, and return its coefficients or its zeros, poles and gain.

## Syntax

    [b, a] = cheby1(n, Rp, Wp)
    [b, a] = cheby1(n, Rp, Wp, ftype)
    [b, a] = cheby1(n, Rp, Wp, 's')
    [b, a] = cheby1(n, Rp, Wp, ftype, 's')
    [z, p, k] = cheby1(___)

## Description

`cheby1(n, Rp, Wp)` designs a digital lowpass Chebyshev type I filter of order `n` whose passband ripple is `Rp` decibels. It returns the numerator `b` and denominator `a` as row vectors; with one output only `b` is returned.

`Wp` is the passband edge, normalised so that 1 is the Nyquist frequency. A scalar gives a lowpass filter, and a two-element `[w1 w2]` gives a bandpass filter. The text options `'low'`, `'high'`, `'bandpass'` and `'stop'` (also `'bandstop'`) choose the type, as in [butter](butter).

With `'s'` the design is analog: `Wp` is in rad/s and `b`, `a` are the coefficients in `s`. For `cheby1(3, 1, 5, 's')` the denominator is `[1 4.9417 30.9602 61.4133]`.

With three outputs it returns zeros and poles as columns and the gain; for `cheby1(2, 1, 0.3)` the gain is 0.1382.

The limits are those of [butter](butter): the arguments go to SciPy unchecked, a digital edge outside (0, 1) is a `ValueError`, a non-integer `n` is truncated, an unknown text option is ignored. The four-output state-space form `[A, B, C, D]` is one realisation of the filter and need not match MATLAB's matrices entry by entry.

## Example

```matlab
[b, a] = cheby1(3, 1, 0.3)
```

This prints `b = [0.0344 0.1032 0.1032 0.0344]` and `a = [1 -1.5804 1.2538 -0.3984]`.

## See also

[butter](butter) · [ellip](ellip) · [filter](filter) · [freqz](freqz) · [filtfilt](filtfilt)
