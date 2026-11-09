# int8

Convert to the int8 integer class.

## Syntax

    B = int8(A)

## Description

`int8(A)` rounds `A` to the nearest integer (halves away from zero) and saturates it to the range -128 to 127: `int8(1000)` is the largest value if that is out of range, and `NaN` becomes 0. Arithmetic on `int8` values rounds and saturates the same way. A `int8` and a double give a `int8`; a `int8` and any other integer class is an error. Arithmetic is carried out in double, so `int64` and `uint64` values beyond 2^53 are not exact.

## Example

```matlab
a = int8(200) + int8(100)
class(a)
b = int8([1.5 2.5 -2.5])
```

## See also

[intmax](intmax) · [intmin](intmin) · [double](double) · [cast](cast)
