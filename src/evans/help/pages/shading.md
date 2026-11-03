# shading

Choose how surfaces are coloured: with grid lines or without.

## Syntax

    shading faceted
    shading flat
    shading interp

## Description

`shading` changes the surfaces and patches already on the current axes. `faceted`, the default, draws each face in one colour with the grid lines in black. `flat` leaves the grid lines off. `interp` leaves them off and smooths the shading across the surface.

Call it after [surf](surf); a surface drawn later starts faceted again.

## Example

```matlab
surf(peaks(30)); shading interp
```

## See also

[surf](surf) · [mesh](mesh) · [colormap](colormap)
