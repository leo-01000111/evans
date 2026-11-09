# rowfun

Apply a function to each row of a table.

## Syntax

    B = rowfun(fun, T)
    B = rowfun(fun, T, 'OutputVariableNames', name, 'InputVariables', vars)

## Description

`fun` gets the variables of a row as separate arguments and returns one value. With `'GroupingVariables'` it gets each group's columns instead.

## Example

```matlab
T = table([1;2;3],[4;5;6],'VariableNames',{'a','b'});
rowfun(@(a,b) a+b, T, 'OutputVariableNames', 's')
```

## See also

[varfun](varfun)
