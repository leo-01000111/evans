# evalin

Run MATLAB text in the base workspace.

## Syntax

    evalin('base', expression)
    y = evalin('base', expression)

## Description

Only the `'base'` workspace is supported. The `'caller'` workspace is refused with an error, since Evans does not keep a function's variables where another function can reach them.

## Example

```matlab
k = 4;
evalin('base', 'k + 1')
```

## See also

[eval](eval) · [feval](feval)
