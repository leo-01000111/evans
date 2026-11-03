# erfc

Complementary error function.

## Syntax

    y = erfc(x)

## Description

erfc(x) = 1 − erf(x), computed directly, so it stays accurate for large `x` where `1 - erf(x)` rounds to 0.

## Example

```matlab
erfc(5)
1 - erf(5)
```

## See also

[erf](erf) · [erfcinv](erfcinv)
