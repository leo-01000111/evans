# log10

Base-10 logarithm of each element.

## Syntax

    Y = log10(X)

## Description

`log10(X)` returns the common logarithm of every element of `X`, with the same size as `X`: `log10(1000)` is 3, and a matrix gives a matrix of the same shape. An empty input gives an empty result.

Zero, negative and complex input:

- `log10(0)` is `-Inf` (no error).
- A negative number gives a complex result instead of `NaN`: `log10(-100)` prints `2 + 1.3644i`. In a vector with one negative element the whole result is complex, so `log10([10 -10])` prints `1 + 0i   1 + 1.3644i`.
- A complex number is accepted: `log10(1+1i)` prints `0.1505 + 0.3411i`.
- `log10(Inf)` is `Inf` and `log10(NaN)` is `NaN`.

A `single` input gives a `single`: `class(log10(single(100)))` is `'single'`. Text, a cell array or a struct stops with "Undefined function 'log10' for input arguments of type 'char'." (with its own type), and `log10(1, 2)` with "Too many input arguments."

A symbolic input stays symbolic: `log10(sym('x'))` prints `log(x)/log(10)`.

Limits of Evans:

- An integer input gives a `double`: `log10(int8(100))` has class `'double'`, and `log10(true)` is 0.

## Example

```matlab
log10([1 10 100 1000])
log10(0)
log10(-100)
```

The first line prints `0 1 2 3`, the second `-Inf`, the third `2 + 1.3644i`.

## See also

[log2](log2) · [exp](exp) · [sqrt](sqrt) · [abs](abs) · [nthroot](nthroot)
