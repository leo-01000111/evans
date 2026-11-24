# butter

Design a Butterworth filter and return its coefficients, or its zeros, poles and gain.

## Syntax

    [b, a] = butter(n, Wn)
    [b, a] = butter(n, Wn, ftype)
    [b, a] = butter(n, Wn, 's')
    [b, a] = butter(n, Wn, ftype, 's')
    [z, p, k] = butter(___)

## Description

`butter(n, Wn)` designs a digital Butterworth filter of order `n` and returns the numerator `b` and denominator `a` as row vectors. With one output, `b = butter(n, Wn)` returns only the numerator.

`Wn` is the cutoff frequency, normalised so that 1 is the Nyquist frequency (half the sampling rate). A scalar `Wn` gives a lowpass filter, and a two-element `Wn = [w1 w2]` gives a bandpass filter. Add `'low'`, `'high'`, `'bandpass'` or `'stop'` (also `'bandstop'`) to choose the type. A two-element `Wn` with `'stop'` is a bandstop filter. A bandpass or bandstop filter of order `n` has `2n+1` coefficients in each of `b` and `a`.

With the option `'s'` the design is analog: `Wn` is in rad/s, with no upper limit, and `b` and `a` are the coefficients of the transfer function in `s`. For example, `butter(2, 100, 's')` gives `a = [1 141.4214 10000]`.

With three outputs, `[z, p, k] = butter(...)` returns the zeros and poles as column vectors and the gain `k`. For `butter(2, 0.2)` the zeros are both -1 and `k` is 0.0675.

Evans passes the arguments to SciPy and does not check them itself:

- A digital `Wn` outside the open interval (0, 1) fails with `ValueError: Digital filter critical frequencies must be 0 < Wn < 1`.
- A non-integer `n` is truncated: `butter(2.5, 0.2)` is the same filter as `butter(2, 0.2)`.
- A text option that is not recognised, such as `'foo'`, is ignored without an error.
- A two-element `Wn` with `'low'` or `'high'`, or a three-element `Wn`, fails with `ValueError: Must specify a single critical frequency Wn for lowpass or highpass filter`.
- The four-output state-space form `[A, B, C, D] = butter(...)` does not work: it fails with `ValueError: 'ss' is not a valid output form.`
- Calling `butter(2)` with no `Wn` fails with a Python `TypeError` about a missing argument.

## Example

```matlab
[b, a] = butter(2, 0.2)
dc = sum(b) / sum(a)
```

The coefficients are `b = [0.0675 0.1349 0.0675]` and `a = [1 -1.1430 0.4128]`. The filter has unit gain at DC, so `dc` prints as 1.0000.

## See also

[cheby1](cheby1) · [ellip](ellip) · [filter](filter) · [freqz](freqz) · [filtfilt](filtfilt) · [designfilt](designfilt)
