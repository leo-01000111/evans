# smoothdata

Smooth noisy data with a moving average or moving median.

## Syntax

    B = smoothdata(A, 'movmean', k)
    B = smoothdata(A, 'movmedian', k)
    B = smoothdata(A, dim, method, k)
    B = smoothdata(..., 'includenan')

## Description

`smoothdata(A, 'movmean', k)` is [movmean](movmean) with window `k` (a length or `[kb kf]`), and `'movmedian'` is [movmedian](movmedian). The window shrinks at the ends. Unlike those two, `smoothdata` ignores `NaN` values by default; `'includenan'` keeps them.

Evans needs the window: MATLAB picks one with a heuristic when it is left out, and Evans does not reproduce that heuristic, so `smoothdata(A)` without a window is refused. The `'gaussian'`, `'lowess'`, `'loess'`, `'rlowess'`, `'rloess'` and `'sgolay'` methods, `'SmoothingFactor'` and `'SamplePoints'` are not supported yet.

## Example

```matlab
t = linspace(0, 1, 50);
x = sin(2*pi*t) + 0.2*cos(40*t);
y = smoothdata(x, 'movmean', 5);
plot(t, x, t, y)
```

## See also

[movmean](movmean) · [movmedian](movmedian) · [detrend](detrend)
