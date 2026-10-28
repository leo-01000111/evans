# tril

Lower triangular part of a matrix.

## Syntax

    L = tril(A)
    L = tril(A, k)

## Description

`tril(A)` keeps the main diagonal and everything below it and sets the rest to zero. `tril(A, k)` keeps diagonal `k` and below: `k = -1` starts just below the main diagonal, `k = 1` just above.

## Example

```matlab
A = [1 2 3; 4 5 6; 7 8 9];
tril(A)
tril(A, -1)
```

## See also

[triu](triu) · [eye](eye) · [lu](lu)
