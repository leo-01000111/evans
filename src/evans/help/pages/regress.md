# regress

Multiple linear regression by least squares.

## Syntax

    b = regress(y, X)
    [b, bint] = regress(y, X)
    [b, bint, r, rint, stats] = regress(y, X)
    [...] = regress(y, X, alpha)

## Description

`regress(y, X)` returns the column `b` of coefficients that best fits `y` (a column of `n` responses) as `X*b` (an `n`-by-`p` matrix of predictors) in the least-squares sense. `regress` does not add an intercept: include a column of ones in `X` for one.

`bint` holds 95% confidence intervals for the coefficients (`alpha` sets the level, default 0.05), `r` the residuals, and `rint` intervals for the residuals, used to spot outliers. `stats` is `[R2 F p s2]`: the R-squared, the F statistic and its p-value, and the error variance; R-squared and F assume `X` has a column of ones.

Rows with `NaN` are left out. If `X` is rank deficient, coefficients of dependent columns are set to 0. Evans does not support `fitlm` yet.

## Example

```matlab
x = (1:6)';
y = [2.1 3.9 6.2 7.8 10.1 12.2]';
X = [ones(6, 1) x];
[b, bint, r, rint, stats] = regress(y, X);
b
```

## See also

[corrcoef](corrcoef) · [pinv](pinv) · [qr](qr)
