# peaks

MATLAB's demonstration surface: two peaks and a pit.

## Syntax

    Z = peaks
    Z = peaks(n)
    Z = peaks(X, Y)
    [X, Y, Z] = peaks(n)
    peaks

## Description

`peaks(n)` returns an n-by-n matrix: a smooth function of two variables with peaks and a pit, sampled over [-3, 3] in both directions. It is handy for trying out [surf](surf), [contour](contour) and [colormap](colormap). `n` is 49 if not given; `peaks(X, Y)` evaluates it on a grid of your own, and `[X, Y, Z] = peaks(n)` returns the grid too.

`peaks` on its own, with no output, draws it with `surf`.

## Example

```matlab
contourf(peaks(40), 10); colorbar
```

## See also

[surf](surf) · [contour](contour) · [meshgrid](meshgrid)
