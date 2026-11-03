# colorbar

Show the colour scale beside the axes.

## Syntax

    colorbar
    colorbar(location)
    colorbar('off')

## Description

`colorbar` puts a bar beside the current axes that shows which colour of the [colormap](colormap) stands for which value. It needs something on the axes drawn through the colour map: a surface, an image, a filled contour or colour-mapped markers.

`location` is `'eastoutside'` (the default), `'westoutside'`, `'northoutside'` or `'southoutside'`; in the figure area the bar is always on the right. `colorbar('off')` removes it. `'Label'` gives the bar a caption.

## Example

```matlab
imagesc([8 1 6; 3 5 7; 4 9 2]); colorbar
```

## See also

[colormap](colormap) · [caxis](caxis) · [imagesc](imagesc) · [surf](surf)
