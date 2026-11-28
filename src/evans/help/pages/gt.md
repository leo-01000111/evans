# gt

Greater-than comparison, the function form of the `>` operator.

## Syntax

    C = gt(A, B)
    C = A > B

## Description

`gt(A, B)` is the same as `A > B`. It returns a logical result, 1 where `A` is greater than `B` and 0 elsewhere. `gt(3, 2)` is 1, and `class(gt(2, 1))` is `'logical'`. Because it is a function it can be passed on, for example `f = @gt; f(2, 1)`. `NaN` is never greater than anything: `gt(NaN, 1)` is 0.

Sizes:

- A scalar is compared with every element: `gt([1 5 3], 2)` is `0 1 1`.
- A row against a column expands to a matrix: `gt([1 2 3]', [1 2 3])` gives the 3-by-3 matrix with 1 below the diagonal.
- A matrix against a row or column vector is expanded the same way, and arrays of more than two dimensions are compared elementwise too.
- An empty input gives an empty result: `gt([], 1)` is `[]`.
- Mismatched sizes stop with "Arrays have incompatible sizes for this operation.": `gt([1 2 3], [1 2])` and `gt(ones(2,3), ones(3,2))`.

Text:

- Characters are compared by code, one by one: `gt('b', 'a')` is 1 and `gt('abc', 'abd')` is `0 0 0`.
- Strings of different lengths stop with "Arrays have incompatible sizes; use strcmp to compare text." A one-character string is compared with every character of the other.
- Double-quoted strings work too: `gt("b", "a")` is 1.

Other types:

- Integer types: `gt(int8(5), 3)` is 1. Two different integer classes, `gt(int8(5), int16(3))`, are refused with a message that talks about the operator `+`.
- Symbolic input stays symbolic: `gt(sym('x'), 2)` prints `x > 2`.
- Dates and durations compare with `gt` as well (`gt(datetime(2020,1,1), datetime(2019,1,1))` is 1).
- Complex numbers are compared by their real parts, as in MATLAB: `gt(2+3i, 1)` is 1 and `gt(1+3i, 1+2i)` is 0.
- A number against a character compares its code: `gt(1, 'a')` is 0.
- A cell array or a struct is refused: `gt({1}, {2})` stops with "Operator '>' is not supported for operands of type 'cell'." So is a function handle.
- `gt(1)` stops with "Not enough input arguments."


## Example

```matlab
x = [1 5 3 8];
gt(x, 2)
x(gt(x, 4))
```

The first line prints `0 1 1 1`; the second picks the elements above 4 and prints `5 8`.

## See also

[isequal](isequal) · [max](max) · [find](find) · [true](true) · [false](false)
