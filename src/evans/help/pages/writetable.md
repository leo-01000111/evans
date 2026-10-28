# writetable

Write a table to a delimited text file, names first.

## Syntax

    writetable(T)
    writetable(T, filename)
    writetable(T, filename, Name, Value)

## Description

The first line is the column names, then one line per row. Text that holds the delimiter or a quote is quoted. With no file name it writes `T.txt`, named after the variable. `'Delimiter'`, `'WriteVariableNames'` and `'WriteMode', 'append'` are supported.

Evans writes text files only, not spreadsheets.

## Example

```matlab
t = [0; 1; 2];
v = [1.5; 2.5; 3.0];
T = table(t, v);
writetable(T, 'out.csv');
U = readtable('out.csv')
```

## See also

[readtable](readtable) · [table](table) · [writematrix](writematrix)
