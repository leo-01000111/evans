# movmean

Moving average over a sliding window.

## Syntax

    M = movmean(A, k)
    M = movmean(A, [kb kf])
    M = movmean(A, k, dim)
    M = movmean(..., 'Endpoints', e)
    M = movmean(..., 'omitnan')

## Description

`movmean(A, k)` replaces each element with the mean of a window of `k` elements around it: for odd `k`, `(k-1)/2` on each side; for even `k`, the element, `k/2` before it and `k/2-1` after it. `[kb kf]` gives `kb` elements before and `kf` after.

A vector keeps its orientation; a matrix is averaged down each column, or along `dim`. Near the ends the window shrinks to the elements that exist (`'Endpoints', 'shrink'`, the default); `'discard'` keeps only full windows, and a number fills the incomplete ones with it.

A window containing `NaN` gives `NaN`, unless `'omitnan'`. Evans does not support non-integer windows or `'SamplePoints'`.

## Example

```matlab
x = [4 8 6 -1 -2 -3 -1 3 4 5];
movmean(x, 3)
```

## See also

[movmedian](movmedian) · [smoothdata](smoothdata) · [mean](mean) · [conv](conv)
