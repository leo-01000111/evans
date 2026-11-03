# array2table

Make a table from the columns of a matrix or cell array.

## Syntax

    T = array2table(A)
    T = array2table(A, 'VariableNames', names)

## Description

Each column of `A` becomes a table variable, named `A1`, `A2`, … unless `'VariableNames'` gives a cell of names. A cell array works too, as long as each of its columns is all numbers or all text.

Evans does not support `'RowNames'`.

## Example

```matlab
T = array2table([1 2; 3 4; 5 6], 'VariableNames', {'t', 'y'})
T.y
```

## See also

[table](table) · [table2array](table2array) · [readtable](readtable)
