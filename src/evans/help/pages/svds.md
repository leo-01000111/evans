# svds

A few singular values of a large matrix.

## Syntax

    s = svds(A)
    s = svds(A, k)
    [U, S, V] = svds(A, k)

## Description

The `k` (default 6) largest singular values; `svds(A, k, 'smallest')` the smallest.

## Example

```matlab
A = sparse(diag(1:8));
svds(A, 3)'
```

## See also

[eigs](eigs) · [svd](svd)
