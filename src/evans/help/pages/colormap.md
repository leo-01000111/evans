# colormap

Set the colours that data values are drawn in.

## Syntax

    colormap(name)
    colormap(map)
    colormap(name, n)
    cmap = colormap

## Description

`colormap` sets the map that surfaces, images, contours, pies and colour-mapped markers in the current figure take their colours from. The lowest value takes the first row of the map and the highest the last; [caxis](caxis) says which values those are.

`name` is one of MATLAB's maps: `parula` (the default), `jet`, `turbo`, `hot`, `cool`, `gray`, `bone`, `copper`, `pink`, `hsv`, `spring`, `summer`, `autumn`, `winter` and `lines`. matplotlib's `viridis`, `plasma`, `inferno`, `magma` and `cividis` work too. Each name is also a function: `jet(8)` returns that map as an 8-by-3 matrix, for `colormap(jet(8))` or to change before use. `parula` is MathWorks' own map; Evans uses viridis, the open map closest to it, in its place.

`map` is any n-by-3 matrix of RGB values between 0 and 1. `cmap = colormap` returns the current map.

## Example

```matlab
surf(peaks(30)); colormap(hot); colorbar
```

## See also

[colorbar](colorbar) · [caxis](caxis) · [surf](surf) · [imagesc](imagesc)
