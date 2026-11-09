# addvars

Add variables to a table.

## Syntax

    T2 = addvars(T, v1, ..., 'NewVariableNames', names)
    T2 = addvars(T, ..., 'Before', var)

## Description

`'Before'` or `'After'` places them next to an existing variable; otherwise they go last.

## Example

```matlab
T = table([1;2],'VariableNames',{'a'});
addvars(T, [5;6], 'NewVariableNames', {'b'})
```

## See also

[removevars](removevars)
