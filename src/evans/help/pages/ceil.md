# ceil

Round toward positive infinity.

## Syntax

    Y = ceil(X)

## Description

`ceil(X)` rounds each element of `X` up to the next integer: `ceil(2.1)` is 3, `ceil(-1.5)` is -1, and a value that is already whole stays as it is. The result has the shape of `X`, for a scalar, a vector, a matrix or an array with more than two dimensions. `Inf`, `-Inf` and `NaN` are returned unchanged, and `ceil([])` is `[]`.

The class is kept for `single` and for integer types: `ceil(single(2.5))` is a `single` and `ceil(int8(5))` is an `int8`. A logical `true` gives the number 1 of class `double`.

Characters are rounded as their codes: `ceil('a')` is 97. A complex number is rounded in each part: `ceil(1.5+2.5i)` is `2 + 3i`. A string, a cell array or a struct stops with "Undefined function 'ceil' for input arguments of type 'cell'." (with its own type).

Limits of Evans:

- One argument only: there is no digits argument. `ceil(1, 2)` stops with "Too many input arguments." and `ceil()` with "Not enough input arguments."
- A symbolic value, `ceil(sym('x'))`, stops with a `TypeError` about `Sym`.

## Example

```matlab
ceil([-1.5 -0.2 0 0.2 1.5 2])
n = ceil(7/2)
```

The first line prints `-1 0 0 1 2 2`, and `n` is 4: four boxes are needed to hold 7 items, 2 to a box.

## See also

[idivide](idivide) · [abs](abs) · [sqrt](sqrt)
