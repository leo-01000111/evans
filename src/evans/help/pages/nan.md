# nan

The value Not-a-Number, written `nan` or `NaN`.

## Syntax

    x = nan
    x = NaN

## Description

`nan` is the constant Not-a-Number, a `double`: `class(nan)` is `'double'`. `nan` and `NaN` are the same constant. It is what `0/0` and similar undefined results give, and it can be tested with `isnan`.

`NaN` is not equal to anything, itself included: `nan == nan` is 0, and `[1 nan] > 0` is `1 0`. `nan + 1` is `NaN`, so a sum that meets a `NaN` is `NaN`: `sum([1 nan])` is `NaN`. `max([1 nan 3])` skips it and returns 3, and `sort([3 nan 1])` puts it last: `1 3 NaN`.

Limits of Evans:

- Only the constant exists. The array forms `nan(n)`, `nan(m, n)`, `nan(m, n, p)`, `nan([m n])`, and `nan(..., 'single')` or `nan('like', x)` do not work: `nan(2)` and `nan(2, 3)` stop with "Index exceeds the number of array elements. Index must not exceed 1.", `nan(0)` and `nan(-1)` with "Index in position 1 is invalid. Array indices must be positive integers", and `NaN(2)` behaves the same. The parentheses are read as indexing the scalar, so `nan()` is the one call that works and returns `NaN`.
- To make an array of `NaN`, scale an array of ones, repeat the constant or fill by index:
  `nan*ones(2, 3)`, `repmat(nan, 1, 3)`, or `x = ones(2, 2); x(:) = nan`.
- `nan` is an ordinary name, so `nan = 5` creates a variable that hides the constant. Do not `clear` it afterwards: `nan = 5; clear nan; nan` fails with "NameError: name 'nan' is not defined", and the constant stays gone for the rest of the session (`clear all` does not bring it back).

## Example

```matlab
x = [1 nan 3];
isnan(x)
y = nan*ones(2, 3)
```

The first result is `0 1 0`; `y` is a 2-by-3 matrix of `NaN`.

## See also

[zeros](zeros) · [ones](ones) · [repmat](repmat) · [max](max) · [sum](sum) · [sort](sort)
