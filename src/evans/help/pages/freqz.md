# freqz

Frequency response of a digital filter.

## Syntax

    [h, w] = freqz(b, a, n)
    [h, f] = freqz(b, a, n, fs)
    [h, w] = freqz(b, a, n, 'whole')
    [h, w] = freqz(b, a, w)
    h = freqz(b)
    freqz(b, a)
    [h, w] = freqz(d, ...)

## Description

`freqz(b, a, n)` evaluates the response of the filter with numerator `b` and denominator `a` at `n` equally spaced points from 0 up to, but not including, pi rad/sample. `h` is a complex column vector, `w` the frequencies as a column. `a` defaults to 1 and `n` to 512.

With a sampling frequency, `freqz(b, a, n, fs)`, the frequencies are in Hz from 0 up to `fs/2` (not included). `'whole'` covers the whole circle, 0 to 2*pi (or `fs`), again without the end point.

If `n` is a vector, those are the frequencies to evaluate at, in rad/sample (or in Hz when `fs` is given). `h = freqz(b)` gives only the response, a column.

Called with no output, `freqz` opens a figure with the magnitude in dB over the phase in degrees. `d` may be a `designfilt` filter in place of `b, a`.

`b` and `a` are read as vectors: a matrix is flattened without a message. Asking for three outputs stops with "Too many output arguments." A call with no argument stops with a Python error message.

## Example

```matlab
[h, w] = freqz([1 1], 1, 4);
abs(h)'
w'
[h2, f] = freqz([1 1]/2, 1, 4, 100);
f'
```

`abs(h)` is `2 1.8478 1.4142 0.7654`; `w` is `0 0.7854 1.5708 2.3562` (multiples of pi/4); `f` is `0 12.5 25 37.5` Hz.

## See also

[filter](filter) · [grpdelay](grpdelay) · [impz](impz) · [butter](butter) · [fft](fft)
