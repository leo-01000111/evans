# contourf

Draw filled contours of a matrix.

## Syntax

    contourf(Z)
    contourf(X, Y, Z)
    contourf(..., n)
    contourf(..., levels)

## Description

`contourf` takes the same inputs as [contour](contour) but fills each band between two levels with the colour of the [colormap](colormap) at its middle, with the contour lines drawn over it in black. [colorbar](colorbar) shows which colour is which value.

## Example

```matlab
contourf(peaks(50), 12); colorbar
```

## See also

[contour](contour) · [imagesc](imagesc) · [colorbar](colorbar)
