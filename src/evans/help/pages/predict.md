# predict

Evaluate a fitted linear model.

## Syntax

    yhat = predict(mdl, Xnew)

## Description

`Xnew` is a matrix of predictor columns, or a table holding them.

## Example

```matlab
mdl = fitlm([1;2;3;4], [2.1;3.9;6.2;7.8]);
predict(mdl, [5;6])
```

## See also

[fitlm](fitlm)
