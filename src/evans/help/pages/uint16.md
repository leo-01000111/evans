# uint16

Convert to the uint16 integer class.

## Syntax

    B = uint16(A)

## Description

`uint16(A)` rounds `A` to the nearest integer (halves away from zero) and saturates it to the range 0 to 65535: `uint16(1000)` is the largest value if that is out of range, and `NaN` becomes 0. Arithmetic on `uint16` values rounds and saturates the same way. A `uint16` and a double give a `uint16`; a `uint16` and any other integer class is an error. Arithmetic is carried out in double, so `int64` and `uint64` values beyond 2^53 are not exact.

## Example

```matlab
a = uint16(200) + uint16(100)
class(a)
b = uint16([1.5 2.5 -2.5])
```

## See also

[intmax](intmax) · [intmin](intmin) · [double](double) · [cast](cast)
