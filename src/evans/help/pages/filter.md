# filter

Apply a digital filter to data.

## Syntax

    y = filter(b, a, x)
    y = filter(b, a, x, zi)
    y = filter(b, a, x, zi, dim)
    [y, zf] = filter(b, a, x, ...)
    y = filter(d, x)

## Description

`filter(b, a, x)` runs the difference equation with numerator coefficients `b` and denominator coefficients `a` over `x`, starting from rest. The output has the size of `x`. A vector is filtered along its length; a matrix is filtered down each column, or along `dim` if given (`filter(b, a, x, [], 2)` filters each row).

`a(1)` may be any non-zero value: `b` and `a` are scaled by it. A zero `a(1)` stops with "First denominator filter coefficient must be non-zero." With fewer than three arguments the error is "Not enough input arguments."

`zi` is the initial state, one value per column, `max(length(a), length(b)) - 1` of them. With a second output `zf` the final state comes back, so a long signal can be filtered in blocks: pass `zf` of one block as `zi` of the next. A `zi` of the wrong length stops with a Python error message.

`filter(d, x)` applies a filter made by `designfilt`. It takes no `zi` and gives no state.

Evans filters in the forward direction only; for zero-phase filtering see `filtfilt`.

## Example

```matlab
y = filter(1, [1 -0.5], [1 0 0 0 0])
[y1, z] = filter(1, [1 -0.5], [1 1 1]);
y2 = filter(1, [1 -0.5], [1 1 1], z)
```

`y` is the impulse response of a first-order filter, `1 0.5 0.25 0.125 0.0625`. `y1` is `1 1.5 1.75`, and `z` is 0.875. Feeding `z` back in makes `y2` continue the same run: `1.875 1.9375 1.9688`.

## See also

[filtfilt](filtfilt) · [conv](conv) · [freqz](freqz) · [butter](butter) · [fft](fft)
