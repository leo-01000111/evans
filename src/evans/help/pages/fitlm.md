# fitlm

Fit a linear model by least squares.

## Syntax

    mdl = fitlm(X, y)
    mdl = fitlm(T, 'y ~ x1 + x2')
    mdl = fitlm(T)

## Description

With a table and no formula the last variable is the response. Formulas have linear terms only, with `-1` for no intercept. `mdl.Coefficients` is a table (row names `(Intercept)`, `x1` ...) with Estimate, SE, tStat and pValue. Also `mdl.Rsquared.Ordinary`, `.Adjusted`, `mdl.RMSE`, `mdl.MSE`, `mdl.DFE`, `mdl.NumObservations`, `mdl.Fitted`, `mdl.Residuals.Raw`. Showing `mdl` prints the summary. `predict(mdl, Xnew)` evaluates it.

## Example

```matlab
x = [1;2;3;4];
y = [2.1;3.9;6.2;7.8];
mdl = fitlm(x, y);
mdl.Coefficients
mdl.Rsquared.Ordinary
```

## See also

[predict](predict) · [regress](regress)
