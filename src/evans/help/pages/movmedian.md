# movmedian

Moving median over a sliding window.

## Syntax

    M = movmedian(A, k)
    M = movmedian(A, [kb kf])
    M = movmedian(A, k, dim)
    M = movmedian(..., 'Endpoints', e)
    M = movmedian(..., 'omitnan')

## Description

`movmedian(A, k)` replaces each element with the median of a window of `k` elements around it, with the same windows as [movmean](movmean): odd `k` centred, even `k` with `k/2` before and `k/2-1` after, or `[kb kf]`.

The window shrinks at the ends by default (`'Endpoints', 'shrink'`); `'discard'` and a fill value are also supported. A matrix works down each column, or along `dim`. A window containing `NaN` gives `NaN`, unless `'omitnan'`.

Evans does not support non-integer windows or `'SamplePoints'`.

## Example

```matlab
x = [4 8 6 -1 -2 -3 -1 3 4 5];
movmedian(x, 3)
```

## See also

[movmean](movmean) · [smoothdata](smoothdata) · [sort](sort)
