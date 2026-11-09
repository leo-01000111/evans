# int16

Convert to the int16 integer class.

## Syntax

    B = int16(A)

## Description

`int16(A)` rounds `A` to the nearest integer (halves away from zero) and saturates it to the range -32768 to 32767: `int16(1000)` is the largest value if that is out of range, and `NaN` becomes 0. Arithmetic on `int16` values rounds and saturates the same way. A `int16` and a double give a `int16`; a `int16` and any other integer class is an error. Arithmetic is carried out in double, so `int64` and `uint64` values beyond 2^53 are not exact.

## Example

```matlab
a = int16(200) + int16(100)
class(a)
b = int16([1.5 2.5 -2.5])
```

## See also

[intmax](intmax) · [intmin](intmin) · [double](double) · [cast](cast)
