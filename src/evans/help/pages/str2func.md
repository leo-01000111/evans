# str2func

Make a function handle from text.

## Syntax

    fn = str2func(name)
    fn = str2func('@(x) expression')

## Description

The text is either a function name or an anonymous function written out, which is evaluated in the base workspace.

## Example

```matlab
g = str2func('@(t) t*2');
g(4)
h = str2func('sin');
h(0)
```

## See also

[func2str](func2str) · [feval](feval)
