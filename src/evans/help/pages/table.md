# table

A table of named columns, built from column vectors.

## Syntax

    T = table(var1, ..., varN)
    T = table(..., 'VariableNames', names)

## Description

Each input is one column, all with the same number of rows: a numeric column vector or a column cell of char. The column names are the inputs' variable names, or `'VariableNames'` gives them as a cell.

Evans's table supports `T.Name`, `T.Properties.VariableNames`, `T(rows, vars)`, `height`, `width`, `size`, `table2array`, `writetable` and display. Row names, `T{...}`, assigning into a table, `sortrows` and `join` are not supported yet.

## Example

```matlab
x = [1; 2; 3];
y = [10; 20; 30];
T = table(x, y)
T.y(2)
```

## See also

[readtable](readtable) · [writetable](writetable)
