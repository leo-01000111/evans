# readtable

Read a table with named columns from a delimited text file.

## Syntax

    T = readtable(filename)
    T = readtable(filename, Name, Value)

## Description

The first line gives the column names, made into valid MATLAB names (`'Speed (m/s)'` becomes `Speed_m_s_`; the original is kept in `T.Properties.VariableDescriptions`). A column of numbers becomes a numeric column, `NaN` where a field is empty; any other column becomes a column cell of char.

`T.Name` is a column, `T.Properties.VariableNames` the names, `T(rows, vars)` a smaller table, and `height(T)`, `width(T)` and `size(T)` its size. `'ReadVariableNames', false` names the columns `Var1`, `Var2` and so on.

Evans's table is a small one for reading and writing data; joining, sorting and `T{...}` indexing are not supported yet. Spreadsheets (`.xlsx`) are not supported.

## Example

```matlab
fid = fopen('runs.csv', 'w');
fprintf(fid, 'name,time\nA,1.25\nB,0.98\n');
fclose(fid);
T = readtable('runs.csv');
T.time
T.name
```

## See also

[writetable](writetable) · [table](table) · [readmatrix](readmatrix)
