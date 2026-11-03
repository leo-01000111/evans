# hanning

Hann window without its zero end points.

## Syntax

    w = hanning(L)
    w = hanning(L, sflag)

## Description

`hanning(L)` is the middle `L` points of `hann(L+2)`: the same shape as [hann](hann), but without the zeros at each end. It is kept for old code; new code uses `hann`.

## Example

```matlab
hanning(3)'
hann(5)'
```

## See also

[hann](hann) · [hamming](hamming)
