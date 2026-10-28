# qr

QR decomposition: an orthogonal times an upper-triangular matrix.

## Syntax

    R = qr(A)
    [Q, R] = qr(A)
    [Q, R, P] = qr(A)
    [Q, R] = qr(A, 'econ')
    [Q, R, p] = qr(A, 0)

## Description

`[Q, R] = qr(A)` gives a unitary `Q` and an upper-triangular `R` with `A = Q*R`. `R = qr(A)` returns only `R`.

`[Q, R, P] = qr(A)` pivots the columns so that `abs(diag(R))` decreases, with `A*P = Q*R` and `P` a permutation matrix. `'econ'` gives the economy size (`Q` is `m`-by-`n` when `m > n`); `qr(A, 0)` is the economy size with the permutation as a vector `p`, `A(:, p) = Q*R`. `'vector'` and `'matrix'` choose the form of the permutation.

Signs of the columns of `Q` (and rows of `R`) may differ from MATLAB's.

## Example

```matlab
A = [1 2; 3 4; 5 6];
[Q, R] = qr(A, 'econ')
norm(Q*R - A)
```

## See also

[lu](lu) · [chol](chol) · [svd](svd) · [regress](regress)
