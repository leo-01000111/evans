# uint64

Convert to the uint64 integer class.

## Syntax

    B = uint64(A)

## Description

`uint64(A)` rounds `A` to the nearest integer (halves away from zero) and saturates it to the range 0 to 18446744073709551615: `uint64(1000)` is the largest value if that is out of range, and `NaN` becomes 0. Arithmetic on `uint64` values rounds and saturates the same way. A `uint64` and a double give a `uint64`; a `uint64` and any other integer class is an error. Arithmetic is carried out in double, so `int64` and `uint64` values beyond 2^53 are not exact.

## Example

```matlab
a = uint64(200) + uint64(100)
class(a)
b = uint64([1.5 2.5 -2.5])
```

## See also

[intmax](intmax) · [intmin](intmin) · [double](double) · [cast](cast)
