# bin2dec

Convert binary digits, as text, to a number.

## Syntax

    d = bin2dec(str)

## Description

`bin2dec('1010')` is 10. Spaces are ignored; a char matrix or cell gives one number per row.

## Example

```matlab
bin2dec('1010')
bin2dec({'1', '11', '111'})
```

## See also

[dec2bin](dec2bin) · [hex2dec](hex2dec) · [base2dec](base2dec)
