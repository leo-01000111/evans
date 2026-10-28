# orth

Orthonormal basis for the range of a matrix.

## Syntax

    Q = orth(A)
    Q = orth(A, tol)

## Description

`orth(A)` returns a matrix whose columns are an orthonormal basis of the column space of `A`, one column per singular value above `max(size(A)) * eps(max(s))` (or `tol`). The number of columns is the rank of `A`.

The basis is unique only up to sign and rotation, so the signs may differ from MATLAB's.

## Example

```matlab
A = [1 1; 1 1; 0 1];
Q = orth(A)
Q'*Q
```

## See also

[null](null) · [svd](svd) · [qr](qr)
