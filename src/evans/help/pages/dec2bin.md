# dec2bin

Convert a nonnegative integer to its binary digits as text.

## Syntax

    str = dec2bin(d)
    str = dec2bin(d, n)

## Description

`dec2bin(10)` is `'1010'`; `n` pads with zeros to at least `n` digits. `bin2dec` converts back, and `dec2hex` and `hex2dec` do the same in base 16.

## Example

```matlab
dec2bin(10)
dec2bin(5, 8)
bin2dec('1010')
```

## See also


