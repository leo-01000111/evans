# colororder

Set the colours that lines take in turn.

## Syntax

    colororder(C)
    colororder(names)
    colororder('gem')
    colororder('default')
    C = colororder

## Description

`colororder(C)` sets the colours given to the curves of the current figure, in order: the first plotted line takes the first colour, the second the second, and so on, round again after the last. `C` is an n-by-3 matrix of RGB values between 0 and 1, or a cell array of colour names or hex codes.

`colororder('gem')` is MATLAB's own default order (the one [lines](lines) returns), for figures that should look like MATLAB's. `colororder('default')` goes back to the theme's colours, which Evans uses otherwise.

A colour given to a curve itself, in a line spec (`'r--'`) or with `'Color'`, always wins over the order. `C = colororder` returns the current order as a matrix, MATLAB's when none has been set.

## Example

```matlab
colororder({'#d95f02', '#1b9e77', '#7570b3'})
x = linspace(0, 1, 50);
plot(x, x, x, x.^2, x, x.^3)
```

## See also

[plot](plot) · [colormap](colormap) · [lines](lines)
