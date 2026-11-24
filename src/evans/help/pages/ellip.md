# ellip

Design an elliptic (Cauer) filter, with ripple in both bands, and return its coefficients or its zeros, poles and gain.

## Syntax

    [b, a] = ellip(n, Rp, Rs, Wp)
    [b, a] = ellip(n, Rp, Rs, Wp, ftype)
    [b, a] = ellip(n, Rp, Rs, Wp, 's')
    [b, a] = ellip(n, Rp, Rs, Wp, ftype, 's')
    [z, p, k] = ellip(___)

## Description

`ellip(n, Rp, Rs, Wp)` designs a digital lowpass elliptic filter of order `n` with `Rp` decibels of ripple in the passband and a stopband attenuation of `Rs` decibels. It returns the numerator `b` and denominator `a` as row vectors; with one output only `b` is returned.

`Wp` is the passband edge, normalised so that 1 is the Nyquist frequency. A scalar gives a lowpass filter, and a two-element `[w1 w2]` gives a bandpass filter (`ellip(3, 1, 40, [0.2 0.4])` returns 7 coefficients in each of `b` and `a`). The text options `'low'`, `'high'`, `'bandpass'` and `'stop'` (also `'bandstop'`) choose the type, as in [butter](butter). With `'s'` the design is analog and `Wp` is in rad/s.

With three outputs it returns zeros and poles as columns and the gain.

The limits are those of [butter](butter): the arguments go to SciPy unchecked, a digital edge outside (0, 1) is a `ValueError`, a non-integer `n` is truncated, an unknown text option is ignored, and the four-output state-space form is not supported.

## Example

```matlab
[b, a] = ellip(3, 1, 40, 0.3)
```

This prints `b = [0.0555 0.0919 0.0919 0.0555]` and `a = [1 -1.5689 1.2627 -0.3991]`.

## See also

[butter](butter) · [cheby1](cheby1) · [filter](filter) · [freqz](freqz) · [filtfilt](filtfilt)
