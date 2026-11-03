# pie

Draw a pie chart.

## Syntax

    pie(x)
    pie(x, explode)
    pie(x, labels)
    pie(x, explode, labels)

## Description

`pie(x)` draws one slice for each element of `x`, sized by its share of `sum(x)`, labelled with its percentage. The slices go clockwise from the top. If the elements add up to less than 1, they are taken as fractions and the pie is left incomplete, as in MATLAB.

`explode` is a vector the size of `x`: slices where it is non-zero are pulled out from the centre. `labels` is a cell array of text, one per slice, used instead of the percentages.

The slice colours come from the [colormap](colormap).

## Example

```matlab
pie([45 30 15 10], [0 1 0 0], {'motor', 'drive', 'sensors', 'other'}); title('Cost')
```

## See also

[bar](bar) · [colormap](colormap)
