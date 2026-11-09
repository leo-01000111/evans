# movevars

Move table variables.

## Syntax

    T2 = movevars(T, vars, 'Before', ref)
    T2 = movevars(T, vars, 'After', ref)

## Description

Move table variables.

## Example

```matlab
T = table([1;2],[3;4],'VariableNames',{'a','b'});
movevars(T, 'b', 'Before', 'a')
```

## See also

[addvars](addvars)
