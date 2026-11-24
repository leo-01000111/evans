# interp1

Interpolate a function of one variable at query points.

## Syntax

    vq = interp1(x, v, xq)
    vq = interp1(x, v, xq, method)
    vq = interp1(x, v, xq, method, extrapval)
    vq = interp1(x, v, xq, method, 'extrap')
    vq = interp1(v, xq)

## Description

`interp1(x, v, xq)` takes the sample points `x` and the values `v` and returns the values at the query points `xq`. The result has the shape of `xq`. If `v` is a matrix, each column is interpolated and the result has one row per query point and one column per column of `v`. The points `x` may come in any order: Evans sorts them first.

`interp1(v, xq)` takes `x` to be 1, 2, 3, and so on.

The `method` is one of:

- `'linear'` (the default)
- `'nearest'`: a query exactly half-way between two samples takes the upper one
- `'previous'` and `'next'`
- `'spline'`
- `'pchip'`, or `'cubic'`, which is the same as `'pchip'`
- `'makima'`

A leading `*` on the name, as in `'*linear'`, is accepted and ignored. Any other name fails with `Invalid interpolation method 'foo'.`

Outside the range of `x` the result is `NaN`, unless you give a number `extrapval`, which is used instead, or the word `'extrap'`, which extrapolates. The methods `'spline'`, `'pchip'`, `'cubic'` and `'makima'` extrapolate by default. Giving a number turns extrapolation off for these as well. For `x = [1 2 3]` and `v = [10 20 40]`, the query 4 gives `NaN`, `0` with `extrapval` 0, and `60` with `'extrap'`; with `'spline'` it gives 70.

Evans does not check its input. Repeated points in `x` give no error (`interp1([1 2 2 3], [10 20 30 40], 2)` returns 30), and a `NaN` in `xq` gives `NaN`.

## Example

```matlab
x = [1 2 3 4];
v = [1 4 9 16];
interp1(x, v, 2.5)
interp1(x, v, 2.5, 'spline')
interp1(x, v, 5, 'linear', 'extrap')
```

The three results are 6.5, 6.25 and 23.

## See also

[spline](spline) · [pchip](pchip) · [ppval](ppval) · [interp2](interp2) · [polyval](polyval)
