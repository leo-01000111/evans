# hamming

Hamming window.

## Syntax

    w = hamming(L)
    w = hamming(L, sflag)

## Description

A column of `L` samples of 0.54 − 0.46·cos(2πn/(L−1)). `sflag` is `'symmetric'` (the default, for filter design) or `'periodic'` (for spectral analysis). The Hamming window does not reach zero at its ends, which lowers its nearest side lobe compared with [hann](hann).

## Example

```matlab
w = hamming(8)'
```

## See also

[hann](hann) · [blackman](blackman) · [window](window)
