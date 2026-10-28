# lu

LU decomposition with partial pivoting.

## Syntax

    [L, U] = lu(A)
    [L, U, P] = lu(A)
    [L, U, p] = lu(A, 'vector')
    Y = lu(A)

## Description

`[L, U, P] = lu(A)` gives a unit lower-triangular `L`, an upper-triangular `U` and a permutation matrix `P` with `P*A = L*U`. With `'vector'`, `p` is a row of indices with `A(p, :) = L*U`.

`[L, U] = lu(A)` returns `L` already permuted, `P'*L`, so that `A = L*U` (that `L` is not triangular in general). `Y = lu(A)` returns `L` and `U` in one matrix, `L + U - eye`. Rectangular matrices work too.

## Example

```matlab
A = [1 2; 3 4];
[L, U, P] = lu(A)
```

## See also

[qr](qr) · [chol](chol) · [inv](inv) · [det](det)
