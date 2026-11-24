# log2

Base-2 logarithm of each element.

## Syntax

    Y = log2(X)

## Description

`log2(X)` returns the base-2 logarithm of every element of `X`, with the same size as `X`: `log2(1024)` is 10, `log2(3)` prints `1.5850`, and `log2([1 2 4 0.5])` is `0 1 2 -1`. An empty input gives an empty result.

Zero, negative and complex input:

- `log2(0)` is `-Inf` (no error) and `log2(Inf)` is `Inf`.
- A negative number gives a complex result instead of `NaN`: `log2(-8)` prints `3.0000 + 4.5324i`.
- A complex number is accepted: `log2(1+1i)` prints `0.5000 + 1.1331i`.

A symbolic input stays symbolic: `log2(sym('x'))` prints `log(x)/log(2)`.

Limits of Evans:

- Only the one-output form exists. The two-output form `[f, e] = log2(x)` (mantissa and exponent) stops with "Too many output arguments."
- The result is always `double`: `class(log2(single(8)))` is `'double'`, and `log2(int8(8))` is 3.
- It takes exactly one argument. `log2(1, 2)` fails with a Python `TypeError` message ("takes 1 positional argument but 2 were given") rather than a MATLAB-style message.
- Text is not rejected cleanly: `log2('a')` fails with a numpy error message.

## Example

```matlab
log2([1 2 4 8 1024])
log2(0)
```

The first line prints `0 1 2 3 10`, the second `-Inf`.

## See also

[log10](log10) · [exp](exp) · [sqrt](sqrt) · [abs](abs) · [nthroot](nthroot)
