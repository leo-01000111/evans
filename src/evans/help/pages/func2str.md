# func2str

The text of a function handle.

## Syntax

    s = func2str(fn)

## Description

An anonymous function gives back its definition as written, without the space after the argument list, as MATLAB prints it. A handle to a named function gives the name.

## Example

```matlab
f = @(x, y) x.^2 + y;
func2str(f)
func2str(@sin)
```

## See also

[str2func](str2func) · [feval](feval)
