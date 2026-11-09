# feval

Call a function given by name or handle.

## Syntax

    [y1, y2, ...] = feval(fn, x1, x2, ...)

## Description

`fn` is a function handle or the name of a function, a function file or a command. All outputs of the function can be collected.

## Example

```matlab
feval('max', [3 9 2])
[m, i] = feval(@max, [3 9 2])
feval(@plus, 1, 2)
```

## See also

[eval](eval) · [str2func](str2func) · [func2str](func2str) · [cellfun](cellfun)
