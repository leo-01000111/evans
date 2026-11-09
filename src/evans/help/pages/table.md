# table

A table of named columns, built from column vectors.

## Syntax

    T = table(var1, ..., varN)
    T = table(..., 'VariableNames', names)

## Description

Each input is one column, all with the same number of rows: a numeric column vector or a column cell of char. The column names are the inputs' variable names, or `'VariableNames'` gives them as a cell.

A table also takes `'RowNames'`, or `'Size'` with `'VariableTypes'` for an empty one. A variable holds numbers, logicals, text (a cell of char), datetimes or durations.

Index with `T(rows, vars)` (a table), `T{rows, vars}` (the contents, joined into a matrix or cell), `T.Name`, and a row mask: `T(T.x > 2, :)`. Assign with `T.new = col`, `T.x(2) = 5`, `T(2, :) = {1, 'a'}`, `T(end+1, :) = ...`, `T{1, 'x'} = 3`, and delete with `T(rows, :) = []` or `T(:, 'x') = []`. `T.Properties.VariableNames` and `RowNames` can be set. `height`, `width`, `size`, `head`, `tail`, `summary`, `sortrows`, `unique`, `innerjoin`, `outerjoin`, `groupsummary`, `varfun`, `rowfun`, `removevars`, `addvars` and `[T1; T2]` work on it.

Not in Evans: variables that are matrices (one column each), categorical variables, `stack`/`unstack`.

## Example

```matlab
x = [1; 2; 3];
y = [10; 20; 30];
T = table(x, y)
T.y(2)
```

## See also

[readtable](readtable) · [writetable](writetable) · [sortrows](sortrows) · [innerjoin](innerjoin) · [timetable](timetable)
