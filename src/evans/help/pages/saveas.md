# saveas

Save a figure to an image or document file.

## Syntax

    saveas(fig, filename)
    saveas(fig, filename, format)

## Description

`saveas(fig, filename)` writes the figure `fig` to `filename`. The format follows the extension: `.png`, `.jpg`, `.tif`, `.svg`, `.pdf` or `.eps`. `fig` is a figure handle such as the one [gcf](gcf) returns.

When `filename` has no extension, `format` supplies it (`'png'` if neither is given). `'fig'` is accepted and written as a PNG, since Evans has no MATLAB `.fig` files. A relative name is taken from the current folder.

[exportgraphics](exportgraphics) does the same and also sets the resolution; [print](print) is the older form.

## Example

```matlab
plot(0:10, (0:10).^2); title('squares')
saveas(gcf, 'squares.png')
```

## See also

[exportgraphics](exportgraphics) · [print](print) · [gcf](gcf) · [figure](figure)
