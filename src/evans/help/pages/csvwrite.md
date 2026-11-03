# csvwrite

Write a matrix to a comma-separated file.

## Syntax

    csvwrite(filename, M)
    csvwrite(filename, M, R, C)

## Description

`csvwrite` writes `M` row by row, numbers to 5 significant digits, as MATLAB's does. `R` and `C` (0-based) offset the data by that many empty rows and columns.

For full precision use [writematrix](writematrix), which writes 15 significant digits, or [dlmwrite](dlmwrite) with `'precision'`.

## Example

```matlab
csvwrite('m.csv', [pi 2; 3 4]);
M = csvread('m.csv')
```

## See also

[csvread](csvread) · [dlmwrite](dlmwrite) · [writematrix](writematrix)
