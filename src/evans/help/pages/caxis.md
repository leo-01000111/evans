# caxis

Set the range of values the colour map spans.

## Syntax

    caxis([cmin cmax])
    caxis('auto')
    lims = caxis
    clim([cmin cmax])

## Description

`caxis([cmin cmax])` makes `cmin` the first colour of the [colormap](colormap) and `cmax` the last, on the current axes; values outside the range take the end colours. Fixing it keeps several plots on the same scale. `caxis('auto')` goes back to the range of the data, and `lims = caxis` returns the range in use.

`clim` is the newer name for the same function.

## Example

```matlab
imagesc(peaks(40)); caxis([-2 2]); colorbar
```

## See also

[colormap](colormap) · [colorbar](colorbar) · [imagesc](imagesc)
