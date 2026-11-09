# imshow

Show a grayscale image.

## Syntax

    imshow(I)
    imshow(I, [low high])
    imshow(I, [])
    imshow(X, map)

## Description

`imshow(I)` shows the matrix `I` as a grayscale picture, black at 0 and white at 1, with equal pixel sizes and no axes. Values outside [0, 1] are shown as black or white, as MATLAB does with an image of doubles.

`imshow(I, [low high])` shows `low` as black and `high` as white. `imshow(I, [])` stretches the range of `I` itself from black to white, which is what you want for data that is not already in [0, 1], pixel counts from 0 to 255 for example. `imshow(X, map)` shows an indexed image in the colours of `map`, as [image](image) does.

A true-colour image is an m-by-n-by-3 array of red, green and blue values between 0 and 1. Reading image files with `imread` is not in Evans yet.

## Example

```matlab
[X, Y] = meshgrid(linspace(-1, 1, 120));
imshow(exp(-4*(X.^2 + Y.^2)))
```

## See also

[imagesc](imagesc) · [image](image) · [colormap](colormap)
