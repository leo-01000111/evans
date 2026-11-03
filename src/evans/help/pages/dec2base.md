# dec2base

Convert a nonnegative integer to digits in any base.

## Syntax

    str = dec2base(d, base)
    str = dec2base(d, base, n)

## Description

`base` is 2 to 36; digits past 9 are the letters A–Z. `n` pads with zeros. [base2dec](base2dec) converts back. Evans does not support a custom set of symbols.

## Example

```matlab
dec2base(255, 16)
dec2base(10, 3, 5)
```

## See also

[base2dec](base2dec) · [dec2bin](dec2bin) · [dec2hex](dec2hex)
