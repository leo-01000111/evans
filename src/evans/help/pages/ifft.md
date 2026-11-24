# ifft

Inverse discrete Fourier transform.

## Syntax

    x = ifft(X)
    x = ifft(X, n)
    x = ifft(X, n, dim)
    x = ifft(___, 'symmetric')

## Description

`ifft(X)` undoes `fft`: it transforms a vector along its length (or a matrix down its columns) and divides by the number of points, so `ifft(fft(x))` gives back `x`.

`n` cuts or zero-pads `X` to `n` points first, as in `fft`, and `dim` picks the dimension. A `dim` above 2 returns `X` unchanged.

The output is real when `X` is exactly conjugate-symmetric, as the spectrum of a real signal is, and complex otherwise. After a change that spoils the symmetry (a spectrum you modified) the imaginary part stays, even if it is tiny. `'symmetric'` assumes the symmetry: it uses only the first half of `X` and always returns a real signal.

`ifft(X, n)` with an `n` longer than `X` pads the spectrum with zeros at the end, which is not an interpolation of the signal.

## Example

```matlab
x = [1 2 3 4];
y = ifft(fft(x))
isreal(y)
z = ifft([4 1+2i 0 1-2i], 'symmetric')
```

`y` is `1 2 3 4` and `isreal(y)` is 1. `z` is `1.5 0 0.5 2`. Without `'symmetric'`, `ifft([1 2 3 4])` stays complex: `2.5`, `-0.5-0.5i`, `-0.5`, `-0.5+0.5i`.

## See also

[fft](fft) · [filter](filter) · [conv](conv)
