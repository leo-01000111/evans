# table2array

The contents of a table as one matrix.

## Syntax

    A = table2array(T)

## Description

`table2array` puts the table's variables side by side. All-numeric variables give a matrix; all-text variables give a cell array. A table that mixes the two cannot be joined into one array, as in MATLAB; take the variables out one at a time with `T.name`.

## Example

```matlab
T = table([1; 2], [3; 4]);
A = table2array(T)
```

## See also

[array2table](array2table) · [table](table) · [height](height)
