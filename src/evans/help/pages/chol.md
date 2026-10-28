# chol

Cholesky factorisation of a symmetric positive definite matrix.

## Syntax

    R = chol(A)
    L = chol(A, 'lower')
    [R, p] = chol(A)

## Description

`chol(A)` returns the upper-triangular `R` with `R'*R = A`. Only the upper triangle of `A` is used (it is assumed symmetric). `chol(A, 'lower')` returns the lower-triangular `L` with `L*L' = A`, from the lower triangle.

If `A` is not positive definite, `chol(A)` fails with "Matrix must be positive definite." `[R, p] = chol(A)` does not fail: `p = 0` when the factorisation succeeds, otherwise `p` is the column where it broke down and `R` is the factor of `A(1:p-1, 1:p-1)`.

## Example

```matlab
A = [4 2; 2 3];
R = chol(A)
[R2, p] = chol([1 2; 2 1])
```

## See also

[lu](lu) · [qr](qr) · [eig](eig)
