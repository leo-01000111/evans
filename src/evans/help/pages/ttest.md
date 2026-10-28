# ttest

One-sample or paired-sample t-test.

## Syntax

    h = ttest(x)
    h = ttest(x, m)
    h = ttest(x, y)
    [h, p, ci, stats] = ttest(...)
    [...] = ttest(..., 'Alpha', a, 'Tail', t)

## Description

`ttest(x)` tests whether the data in `x` come from a normal distribution with mean 0, against the alternative that the mean is not 0. `h = 1` rejects that at the 5% level, `h = 0` does not. `ttest(x, m)` tests mean `m`. `ttest(x, y)` with `y` the same size as `x` is a paired test on `x - y`.

`p` is the p-value, `ci` the confidence interval for the mean (of `x`, or of `x - y`), and `stats` a struct with fields `tstat`, `df` and `sd`. For a matrix each column is tested; `'Dim'` picks the dimension. `NaN` values are ignored.

`'Alpha'` sets the significance level (default 0.05). `'Tail'` is `'both'` (default), `'right'` (mean greater than `m`) or `'left'`; a one-sided test gives a one-sided interval with an infinite end.

## Example

```matlab
x = [5.1 4.9 5.6 5.8 6.0 5.4 5.3];
[h, p, ci, stats] = ttest(x, 5)
```

## See also

[mean](mean) · [var](var) · [normcdf](normcdf)
