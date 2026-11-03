# image

Show a matrix as an image, its values used as colour map indices.

## Syntax

    image(C)
    image(x, y, C)

## Description

`image(C)` draws each element of `C` in the [colormap](colormap)'s colour of that number: 1 is the first colour, 2 the second, values are rounded down, and anything outside the map takes its first or last colour. Use [imagesc](imagesc) to scale arbitrary data to the map instead.

Images in true colour, an m-by-n-by-3 array, need N-D arrays, which Evans does not have yet.

## Example

```matlab
image([1 2 3; 4 5 6]); colormap(jet(6)); colorbar
```

## See also

[imagesc](imagesc) · [imshow](imshow) · [colormap](colormap)
