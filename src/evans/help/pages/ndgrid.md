# ndgrid

Make grids of points with the first input varying down the rows.

## Syntax

    [X1, X2] = ndgrid(x1, x2)
    [X1, X2, X3] = ndgrid(x1, x2, x3)
    [X1, X2] = ndgrid(x)

## Description

`ndgrid` returns one array per output, each `length(x1)`-by-`length(x2)`-by-... in size: `X1` repeats `x1` down its columns, `X2` repeats `x2` along its rows. It is [meshgrid](meshgrid) with the first two axes swapped, and it works for any number of inputs. With one input and several outputs the vector is used for every dimension.

## Example

```matlab
[X, Y] = ndgrid(1:2, 1:3)
```

## See also

[meshgrid](meshgrid) · [repmat](repmat) · [permute](permute)
