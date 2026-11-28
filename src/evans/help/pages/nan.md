# nan

The value Not-a-Number, written `nan` or `NaN`.

## Syntax

    x = nan
    x = NaN
    X = nan(n)
    X = nan(m, n, ...)
    X = nan([m n])
    X = nan(..., 'single')
    X = nan(..., 'like', p)

## Description

`nan` is the constant Not-a-Number, a `double`: `class(nan)` is `'double'`. `nan` and `NaN` are the same. It is what `0/0` and similar undefined results give, and it can be tested with `isnan`.

With sizes, `nan` makes an array of `NaN`, as `zeros` makes an array of zeros: `nan(2)` is 2-by-2, `nan(2, 3)` and `nan([2 3])` are 2-by-3. `'single'` gives class `single`, and `'like', p` takes the class of `p`. An integer class stops with an error, since integers have no `NaN`. `inf` and `Inf` take the same arguments.

`NaN` is not equal to anything, itself included: `nan == nan` is 0, and `[1 nan] > 0` is `1 0`. `nan + 1` is `NaN`, so a sum that meets a `NaN` is `NaN`: `sum([1 nan])` is `NaN`. `max([1 nan 3])` skips it and returns 3, and `sort([3 nan 1])` puts it last: `1 3 NaN`.

Limits of Evans:

- `nan` is an ordinary name, so `nan = 5` creates a variable that hides it until `clear nan`. After `clear nan`, in the same script or later, `nan` is `NaN` again.

## Example

```matlab
x = [1 nan 3];
isnan(x)
y = nan(2, 3)
```

The first result is `0 1 0`; `y` is a 2-by-3 matrix of `NaN`.

## See also

[zeros](zeros) · [ones](ones) · [repmat](repmat) · [max](max) · [sum](sum) · [sort](sort)
