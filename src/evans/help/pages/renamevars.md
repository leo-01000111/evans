# renamevars

Rename table variables.

## Syntax

    T2 = renamevars(T, old, new)

## Description

`old` is a name or cell of names.

## Example

```matlab
T = table([1;2],'VariableNames',{'a'});
renamevars(T, 'a', 'z')
```

## See also

[addvars](addvars)
