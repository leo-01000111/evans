# int64

Convert to the int64 integer class.

## Syntax

    B = int64(A)

## Description

`int64(A)` rounds `A` to the nearest integer (halves away from zero) and saturates it to the range -9223372036854775808 to 9223372036854775807: `int64(1000)` is the largest value if that is out of range, and `NaN` becomes 0. Arithmetic on `int64` values rounds and saturates the same way. A `int64` and a double give a `int64`; a `int64` and any other integer class is an error. Arithmetic is carried out in double, so `int64` and `uint64` values beyond 2^53 are not exact.

## Example

```matlab
a = int64(200) + int64(100)
class(a)
b = int64([1.5 2.5 -2.5])
```

## See also

[intmax](intmax) · [intmin](intmin) · [double](double) · [cast](cast)
