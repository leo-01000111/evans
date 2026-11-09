# nargin

How many inputs a function takes.

## Syntax

    n = nargin(fn)

## Description

`fn` is a function handle or a name. A function with `varargin` gives a negative number: minus one more than the named inputs. Inside a function file, plain `nargin` is the number of inputs of the current call, as in MATLAB, and `nargin(fn)` is not available there.

## Example

```matlab
f = @(a, b, c) a + b + c;
nargin(f)
```

## See also

[feval](feval) · [func2str](func2str)
