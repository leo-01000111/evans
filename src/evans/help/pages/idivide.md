# idivide

Integer division with a chosen rounding.

## Syntax

    C = idivide(A, B)
    C = idivide(A, B, option)

## Description

Divides integers and rounds the quotient as `option` says: `'fix'` (the default, towards zero), `'floor'`, `'ceil'` or `'round'`. Plain `A / B` always rounds to nearest. At least one input must be an integer class.

## Example

```matlab
idivide(int32(7), int32(2))
idivide(int32(7), int32(2), 'floor')
int32(7) / int32(2)
```

## See also

[int32](int32)
