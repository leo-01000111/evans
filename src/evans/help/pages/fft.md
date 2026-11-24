# fft

Discrete Fourier transform of a vector or of each column of a matrix.

## Syntax

    X = fft(x)
    X = fft(x, n)
    X = fft(x, n, dim)

## Description

`fft(x)` returns the transform of `x`, the same size as `x`, with no scaling: `X(1)` is the sum of the samples. A vector is transformed along its length, whichever way it lies; a matrix is transformed down each column.

`fft(x, n)` cuts `x` to its first `n` samples or pads it with zeros to `n` samples before transforming. An empty `n` (`[]`) leaves the length alone. `n` must be a positive whole number; `fft([1 2 3], -1)` stops with "Invalid number of FFT data points (-1) specified."

`fft(x, n, dim)` works along dimension `dim`, so `fft(A, [], 2)` transforms each row of a matrix. A `dim` above 2 returns `x` unchanged.

The result is complex, even when every imaginary part is zero, so a real spectrum is displayed as `10 + 0i`. Use `abs` and `angle` for magnitude and phase. Only the first and second dimensions are handled: there is no N-D transform.

A call with no argument or with a text argument stops with a Python error message instead of a MATLAB one.

## Example

```matlab
x = [1 2 3 4];
X = fft(x)
abs(X(2))
size(fft(x, 8))
```

`X` is `10`, `-2+2i`, `-2` and `-2-2i`; `abs(X(2))` is 2.8284 and the padded transform has size `1 8`.

For a cosine of 2 Hz sampled at 8 Hz for 1 second (`x = cos(2*pi*2*(0:7)/8)`), `abs(fft(x))` is 4 at bins 3 and 7 (frequencies 2 Hz and 6 Hz) and about 1e-16 elsewhere.

## See also

[ifft](ifft) · [filter](filter) · [periodogram](periodogram) · [pwelch](pwelch)
