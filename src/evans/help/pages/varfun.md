# varfun

Apply a function to each variable of a table.

## Syntax

    B = varfun(fun, T)
    B = varfun(fun, T, 'InputVariables', vars, 'GroupingVariables', g)
    B = varfun(..., 'OutputFormat', fmt)

## Description

`fun` gets each variable (or each group of it) and must return a scalar. Columns are named `Fun_var`. `'OutputFormat'` is `'table'`, `'uniform'` or `'cell'`.

## Example

```matlab
T = table([1;2;3],[4;5;6],'VariableNames',{'a','b'});
varfun(@sum, T)
```

## See also

[rowfun](rowfun) · [groupsummary](groupsummary)
