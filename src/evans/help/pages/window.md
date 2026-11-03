# window

A window by name or by function handle.

## Syntax

    w = window(fhandle, L)
    w = window(fhandle, L, param)
    w = window(name, L, ...)

## Description

`window(@hamming, 64)` is `hamming(64)`. The window can also be given by name: `'hann'`, `'hamming'`, `'blackman'`, `'kaiser'`, `'rectwin'`, `'triang'`, `'bartlett'` or `'hanning'`. Arguments after `L` go to the window function, such as Kaiser's `beta`.

## Example

```matlab
w = window(@kaiser, 5, 2)'
```

## See also

[hann](hann) · [hamming](hamming) · [kaiser](kaiser)
