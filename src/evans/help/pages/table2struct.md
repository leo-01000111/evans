# table2struct

A struct array from a table.

## Syntax

    S = table2struct(T)
    S = table2struct(T, 'ToScalar', true)

## Description

A struct array from a table.

## Example

```matlab
table2struct(table([1;2],'VariableNames',{'a'}))
```

## See also

[table](table)
