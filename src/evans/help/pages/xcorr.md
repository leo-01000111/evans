# xcorr

Cross-correlation of two signals, or autocorrelation of one.

## Syntax

    r = xcorr(x)
    r = xcorr(x, y)
    r = xcorr(..., maxlag)
    r = xcorr(..., scaleopt)
    [r, lags] = xcorr(...)

## Description

`xcorr(x, y)` is `sum(x(n+m) * conj(y(n)))` for each lag `m`, from `-maxlag` to `maxlag` (by default the length minus 1). `scaleopt` is `'none'`, `'biased'`, `'unbiased'` or `'coeff'` (1 at lag 0 for an autocorrelation). `lags` is a row; `r` is a column for column input and a row for row input.

Evans correlates vectors only, not the columns of a matrix.

## Example

```matlab
x = [1 2 3];
[r, lags] = xcorr(x)
```

## See also

[conv](conv)
