# int32

Convert to the int32 integer class.

## Syntax

    B = int32(A)

## Description

`int32(A)` rounds `A` to the nearest integer (halves away from zero) and saturates it to the range -2147483648 to 2147483647: `int32(1000)` is the largest value if that is out of range, and `NaN` becomes 0. Arithmetic on `int32` values rounds and saturates the same way. A `int32` and a double give a `int32`; a `int32` and any other integer class is an error. Arithmetic is carried out in double, so `int64` and `uint64` values beyond 2^53 are not exact.

## Example

```matlab
a = int32(200) + int32(100)
class(a)
b = int32([1.5 2.5 -2.5])
```

## See also

[intmax](intmax) · [intmin](intmin) · [double](double) · [cast](cast)
