# detrend

Remove a straight-line (or polynomial) trend from data.

## Syntax

    y = detrend(x)
    y = detrend(x, 0)
    y = detrend(x, 'constant')
    y = detrend(x, 'linear')
    y = detrend(x, n)

## Description

`detrend(x)` subtracts the least-squares straight line from a vector, or from each column of a matrix; a vector keeps its orientation. `detrend(x, 0)` or `'constant'` subtracts the mean, `detrend(x, 1)` or `'linear'` the line, and `detrend(x, n)` a polynomial of degree `n`.

Evans does not support breakpoints, `'omitnan'` or `'SamplePoints'`, and refuses data containing `NaN`.

## Example

```matlab
x = [1 3 2 5 4 7];
detrend(x)
detrend(x, 0)
```

## See also

[polyval](polyval) · [mean](mean) · [smoothdata](smoothdata)
