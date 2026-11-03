# kaiser

Kaiser window.

## Syntax

    w = kaiser(L)
    w = kaiser(L, beta)

## Description

A column of `L` samples of the Kaiser window. `beta` (0.5 by default) trades main-lobe width against side-lobe level: larger `beta`, lower side lobes, wider main lobe. `beta = 0` is the rectangular window.

## Example

```matlab
w = kaiser(6, 4)'
```

## See also

[window](window) · [blackman](blackman)
