# spdiags

Build a sparse matrix from diagonals, or take diagonals out.

## Syntax

    A = spdiags(B, d, m, n)
    A = spdiags(B, d, A)
    [B, d] = spdiags(A)
    B = spdiags(A, d)

## Description

Column `k` of `B` becomes diagonal `d(k)` of the m-by-n matrix (0 the main diagonal, positive above, negative below). For `m >= n` entries line up with the column, for `m < n` with the row, as in MATLAB. `spdiags(A)` returns the nonzero diagonals; `spdiags(B, d, A)` replaces diagonals of `A`.

## Example

```matlab
n = 5; e = ones(n, 1);
K = spdiags([-e 2*e -e], -1:1, n, n);
full(K)
```

## See also

[sparse](sparse) · [pcg](pcg)
