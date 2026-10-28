# readmatrix

Read a matrix of numbers from a delimited text file.

## Syntax

    A = readmatrix(filename)
    A = readmatrix(filename, Name, Value)

## Description

`readmatrix` reads a `.csv`, `.txt` or `.dat` file into a matrix. It finds the delimiter itself (comma, tab, semicolon or spaces) and skips leading lines that are not numbers, such as a header row. A field that is not a number becomes `NaN`.

The options `'Delimiter'`, `'NumHeaderLines'` and `'Range'` (such as `'B2:C3'`) are supported.

Evans reads text files only: `.xlsx` spreadsheets need openpyxl, which Evans doesn't ship. Numbers are read as `double` only.

## Example

```matlab
fid = fopen('log.csv', 'w');
fprintf(fid, 't,v\n0,1.5\n1,2.5\n2,3.0\n');
fclose(fid);
A = readmatrix('log.csv')
```

## See also

[writematrix](writematrix) · [readtable](readtable) · [fopen](fopen)
