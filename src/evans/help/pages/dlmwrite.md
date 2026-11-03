# dlmwrite

Write a matrix to a delimited text file.

## Syntax

    dlmwrite(filename, M)
    dlmwrite(filename, M, delimiter)
    dlmwrite(filename, M, delimiter, R, C)
    dlmwrite(filename, M, Name, Value)
    dlmwrite(filename, M, '-append', ...)

## Description

`dlmwrite` writes `M` with commas, or with `delimiter`. Numbers have 5 significant digits unless `'precision'` gives a digit count or a format such as `'%.3f'`.

The options are `'delimiter'`, `'roffset'`, `'coffset'`, `'precision'` and `'newline'` (`'pc'` or `'unix'`). `'-append'` adds to the end of the file instead of replacing it.

## Example

```matlab
dlmwrite('m.txt', pi*[1 2; 3 4], 'delimiter', '\t', 'precision', 6);
dlmwrite('m.txt', [9 9], '-append', 'delimiter', '\t');
M = dlmread('m.txt')
```

## See also

[dlmread](dlmread) · [csvwrite](csvwrite) · [writematrix](writematrix)
