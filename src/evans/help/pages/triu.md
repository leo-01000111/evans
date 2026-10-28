# triu

Upper triangular part of a matrix.

## Syntax

    U = triu(A)
    U = triu(A, k)

## Description

`triu(A)` keeps the main diagonal and everything above it and sets the rest to zero. `triu(A, k)` keeps diagonal `k` and above: `k = 1` starts just above the main diagonal, `k = -1` just below.

## Example

```matlab
A = [1 2 3; 4 5 6; 7 8 9];
triu(A)
triu(A, 1)
```

## See also

[tril](tril) · [eye](eye) · [chol](chol)
