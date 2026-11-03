# csvread

Read a comma-separated file of numbers into a matrix.

## Syntax

    M = csvread(filename)
    M = csvread(filename, R, C)
    M = csvread(filename, R, C, range)

## Description

`csvread(filename)` reads a file of comma-separated numbers. `R` and `C` are the row and column to start at, counted from **0**, as MATLAB counts them here. `range` is `[R1 C1 R2 C2]` (0-based) or a spreadsheet range such as `'A2..C5'`.

Empty fields read as 0; a field that is not a number stops with MATLAB's "Mismatch between file and format" error. For files with a header row, [readmatrix](readmatrix) is simpler: it skips the header itself.

## Example

```matlab
fid = fopen('d.csv', 'w'); fprintf(fid, '1,2,3\n4,5,6\n'); fclose(fid);
M = csvread('d.csv')
B = csvread('d.csv', 1, 1)
```

## See also

[dlmread](dlmread) · [csvwrite](csvwrite) · [readmatrix](readmatrix)
