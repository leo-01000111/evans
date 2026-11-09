# uint32

Convert to the uint32 integer class.

## Syntax

    B = uint32(A)

## Description

`uint32(A)` rounds `A` to the nearest integer (halves away from zero) and saturates it to the range 0 to 4294967295: `uint32(1000)` is the largest value if that is out of range, and `NaN` becomes 0. Arithmetic on `uint32` values rounds and saturates the same way. A `uint32` and a double give a `uint32`; a `uint32` and any other integer class is an error. Arithmetic is carried out in double, so `int64` and `uint64` values beyond 2^53 are not exact.

## Example

```matlab
a = uint32(200) + uint32(100)
class(a)
b = uint32([1.5 2.5 -2.5])
```

## See also

[intmax](intmax) · [intmin](intmin) · [double](double) · [cast](cast)
