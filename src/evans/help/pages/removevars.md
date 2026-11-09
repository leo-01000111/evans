# removevars

Delete variables from a table.

## Syntax

    T2 = removevars(T, vars)

## Description

`vars` are names or numbers.

## Example

```matlab
T = table([1;2],[3;4],'VariableNames',{'a','b'});
removevars(T, 'a')
```

## See also

[addvars](addvars)
