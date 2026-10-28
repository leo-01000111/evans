# writematrix

Write a matrix to a delimited text file.

## Syntax

    writematrix(A)
    writematrix(A, filename)
    writematrix(A, filename, Name, Value)

## Description

`writematrix(A, filename)` writes one line per row of `A`, comma-separated for `.csv` and `.txt`, with up to 15 significant digits (`5`, not `5.0`). With no file name it writes `A.txt`, named after the variable.

`'Delimiter'` sets the separator (`','`, `'\t'`, `' '`, `';'`, `'|'`), and `'WriteMode', 'append'` adds to the end of the file.

Evans writes text files only, not `.xlsx`, and writes numbers, not char: use `fprintf` to write text.

## Example

```matlab
A = [1 2.5; 3 4];
writematrix(A, 'm.csv');
B = readmatrix('m.csv')
```

## See also

[readmatrix](readmatrix) · [writetable](writetable) · [fprintf](fprintf)
