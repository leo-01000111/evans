# deal

Copy inputs to outputs.

## Syntax

    [A, B, ...] = deal(X)
    [A, B, ...] = deal(X1, X2, ...)

## Description

`[A, B] = deal(X)` copies `X` to every output. `[A, B] = deal(X1, X2)` hands out the inputs in order; the number of inputs must then match the number of outputs.

## Example

```matlab
[a, b] = deal(1, 2)
[lo, hi] = deal(0)
```

## See also

[cellfun](cellfun) · [arrayfun](arrayfun)
