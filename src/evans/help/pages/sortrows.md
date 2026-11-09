# sortrows

Sort the rows of a matrix, cell column or table.

## Syntax

    B = sortrows(A)
    B = sortrows(A, col)
    B = sortrows(T, vars, direction)
    [B, idx] = sortrows(...)

## Description

`col` is a vector of columns, negative to sort that column downward. For a table, `vars` are variable names or numbers and `direction` is `'ascend'` or `'descend'`, one for all or a cell with one each. Ties keep their order. Missing values go last, or first when descending.

## Example

```matlab
A = [3 1; 1 2; 3 0];
sortrows(A, [1 -2])
T = table([2;1;2], [5;6;4], 'VariableNames', {'a','b'});
sortrows(T, {'a','b'}, 'descend')
```

## See also

[sort](sort) · [table](table)
