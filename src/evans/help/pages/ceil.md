# ceil

Round toward positive infinity.

## Syntax

    Y = ceil(X)

## Description

`ceil(X)` rounds each element of `X` up to the next integer: `ceil(2.1)` is 3, `ceil(-1.5)` is -1, and a value that is already whole stays as it is. The result has the shape of `X`, for a scalar, a vector, a matrix or an array with more than two dimensions. `Inf`, `-Inf` and `NaN` are returned unchanged, and `ceil([])` is `[]`.

The class is kept for `single` and for integer types: `ceil(single(2.5))` is a `single` and `ceil(int8(5))` is an `int8`. A logical `true` gives the number 1 of class `double`.

Limits of Evans:

- One argument only. `ceil(1, 2)` stops with `TypeError: return arrays must be of ArrayType` and `ceil()` with a message about missing arguments; there is no digits argument.
- Complex numbers are not supported: `ceil(1.5+2.5i)` stops with `TypeError: ufunc 'ceil' not supported for the input types`.
- Characters are not accepted either: `ceil('a')` and `ceil("abc")` stop with the same message. Use `ceil(double('a'))`.
- A cell array is not rejected: `ceil({1})` prints `1` instead of an error.
- A symbolic value, `ceil(sym('x'))`, stops with a `TypeError` about `Sym`.

## Example

```matlab
ceil([-1.5 -0.2 0 0.2 1.5 2])
n = ceil(7/2)
```

The first line prints `-1 0 0 1 2 2`, and `n` is 4: four boxes are needed to hold 7 items, 2 to a box.

## See also

[idivide](idivide) · [abs](abs) · [sqrt](sqrt)
