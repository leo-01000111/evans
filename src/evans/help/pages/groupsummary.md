# groupsummary

Summarise a table by groups.

## Syntax

    S = groupsummary(T, groupvars)
    S = groupsummary(T, groupvars, method, datavars)

## Description

`method` is `'mean'`, `'sum'`, `'min'`, `'max'`, `'median'`, `'mode'`, `'std'`, `'var'`, `'range'`, `'nnz'`, `'numunique'`, `'nummissing'`, a function handle, or a cell of these. The result has the group variables, `GroupCount`, then `method_var` columns.

## Example

```matlab
T = table([1;2;1],[5;6;7],'VariableNames',{'k','v'});
groupsummary(T, 'k', 'sum', 'v')
```

## See also

[varfun](varfun) · [findgroups](findgroups)
