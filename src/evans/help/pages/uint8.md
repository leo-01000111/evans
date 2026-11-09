# uint8

Convert to the uint8 integer class.

## Syntax

    B = uint8(A)

## Description

`uint8(A)` rounds `A` to the nearest integer (halves away from zero) and saturates it to the range 0 to 255: `uint8(1000)` is the largest value if that is out of range, and `NaN` becomes 0. Arithmetic on `uint8` values rounds and saturates the same way. A `uint8` and a double give a `uint8`; a `uint8` and any other integer class is an error. Arithmetic is carried out in double, so `int64` and `uint64` values beyond 2^53 are not exact.

## Example

```matlab
a = uint8(200) + uint8(100)
class(a)
b = uint8([1.5 2.5 -2.5])
```

## See also

[intmax](intmax) · [intmin](intmin) · [double](double) · [cast](cast)
