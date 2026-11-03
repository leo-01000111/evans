# dlmread

Read a delimited file of numbers into a matrix.

## Syntax

    M = dlmread(filename)
    M = dlmread(filename, delimiter)
    M = dlmread(filename, delimiter, R, C)
    M = dlmread(filename, delimiter, range)

## Description

`dlmread` is [csvread](csvread) with any delimiter: give it as text (`','`, `'\t'`, `';'`), or leave it out (or `''`) to have Evans detect it from the file. `R`, `C` and `range` count from 0, as in csvread.

## Example

```matlab
fid = fopen('d.txt', 'w'); fprintf(fid, '1;2;3\n4;5;6\n'); fclose(fid);
M = dlmread('d.txt', ';')
c = dlmread('d.txt', ';', [0 2 1 2])
```

## See also

[csvread](csvread) · [dlmwrite](dlmwrite) · [readmatrix](readmatrix)
