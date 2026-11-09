# single

Convert to single precision.

## Syntax

    B = single(A)

## Description

`single(A)` rounds `A` to 32-bit floating point, about seven digits. A `single` and a double give a `single`; a `single` and an integer give the integer class.

## Example

```matlab
x = single(pi)
class(x + 1)
realmax('single')
```

## See also

[double](double) · [realmax](realmax) · [flintmax](flintmax) · [cast](cast)
