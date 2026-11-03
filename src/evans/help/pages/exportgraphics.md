# exportgraphics

Save a figure to a file, at a chosen resolution.

## Syntax

    exportgraphics(fig, filename)
    exportgraphics(fig, filename, 'Resolution', dpi)

## Description

`exportgraphics(gcf, 'result.pdf')` saves the current figure, choosing the format from the file's extension: `.png`, `.jpg` and `.tif` are pictures; `.svg`, `.pdf` and `.eps` are vector graphics. `fig` can be [gcf](figure), a figure number, or an axes handle from [nexttile](nexttile) or `gca`, which saves the figure it belongs to.

PDF and EPS are drawn for print: dark lines on a white page, with the fonts embedded, ready to go into a LaTeX document. PNG, JPG, TIFF and SVG are the figure as it looks in Evans, in the current theme.

`'Resolution'` sets the dots per inch of a picture (the screen's 96 otherwise). `saveas(fig, filename)` and `print('-dpdf', filename)` write the same files.

## Example

```matlab
plot(1:10, (1:10).^2); title('Growth')
exportgraphics(gcf, 'growth.pdf')
```

## See also

[figure](figure) · [plot](plot) · [subplot](subplot)
