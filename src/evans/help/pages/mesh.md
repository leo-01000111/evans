# mesh

Draw a surface as a wire grid.

## Syntax

    mesh(Z)
    mesh(X, Y, Z)
    mesh(X, Y, Z, C)
    meshc(...)

## Description

`mesh` takes the same inputs as [surf](surf) but draws only the grid lines, coloured by height through the [colormap](colormap), with the faces left in the background colour. `meshc` adds a contour plot below.

## Example

```matlab
mesh(peaks(30))
```

## See also

[surf](surf) · [contour](contour) · [meshgrid](meshgrid)
