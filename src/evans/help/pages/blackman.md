# blackman

Blackman window.

## Syntax

    w = blackman(L)
    w = blackman(L, sflag)

## Description

A column of `L` samples of the three-term Blackman window. Its side lobes are lower than [hann](hann)'s and [hamming](hamming)'s, at the cost of a wider main lobe. `sflag` is `'symmetric'` (the default) or `'periodic'`.

## Example

```matlab
w = blackman(7)'
```

## See also

[hann](hann) · [hamming](hamming) · [kaiser](kaiser)
