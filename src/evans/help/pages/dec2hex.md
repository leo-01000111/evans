# dec2hex

Convert a nonnegative integer to hexadecimal digits as text.

## Syntax

    str = dec2hex(d)
    str = dec2hex(d, n)

## Description

`dec2hex(255)` is `'FF'`; `n` pads with zeros to at least `n` digits. [hex2dec](hex2dec) converts back.

## Example

```matlab
dec2hex(255)
dec2hex(10, 4)
```

## See also

[hex2dec](hex2dec) · [dec2bin](dec2bin) · [dec2base](dec2base)
