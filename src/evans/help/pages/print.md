# print

Save a figure to a file, MATLAB's older way.

## Syntax

    print(filename, '-dformat')
    print(fig, filename, '-dformat')
    print(..., '-rdpi')

## Description

`print` writes a figure to a file. `'-dformat'` names the format: `'-dpng'` (the default), `'-djpeg'`, `'-dtiff'`, `'-dsvg'`, `'-dpdf'` or `'-deps'`. `'-r300'` sets the resolution in dots per inch. Other options, such as `'-painters'`, are accepted and ignored. When `filename` has no extension, the format supplies it. The first argument may be a figure handle, as from [gcf](gcf); otherwise the current figure is saved.

Printing to a paper printer is not supported: without a file name, `print` raises an error. Use [saveas](saveas) or [exportgraphics](exportgraphics) in new code.

## Example

```matlab
plot(1:5, [2 4 3 5 1]);
print('trace', '-dpng', '-r150')
```

## See also

[saveas](saveas) · [exportgraphics](exportgraphics) · [gcf](gcf)
