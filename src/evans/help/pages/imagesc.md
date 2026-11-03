# imagesc

Show a matrix as an image, its values scaled to the colour map.

## Syntax

    imagesc(C)
    imagesc(x, y, C)
    imagesc(..., clims)

## Description

`imagesc(C)` draws a rectangle of colour for each element of `C`, coloured through the [colormap](colormap) so that the smallest value of `C` takes the first colour and the largest the last. Row 1 is at the top, as in a matrix, and the axes fit the image.

`x` and `y` place the image: the centre of the first column is at `x(1)` and of the last at `x(end)`, and the same for the rows with `y`. `clims = [low high]` fixes the range the colour map spans, as [caxis](caxis) does.

Hover over the image to read the row, column and value under the cursor, and click to pin a data tip. Add [colorbar](colorbar) for the scale.

## Example

```matlab
imagesc(peaks(40)); colorbar; title('peaks')
```

## See also

[image](image) · [imshow](imshow) · [colormap](colormap) · [colorbar](colorbar) · [caxis](caxis)
