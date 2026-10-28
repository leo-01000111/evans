# null

Orthonormal basis for the null space of a matrix.

## Syntax

    Z = null(A)
    Z = null(A, tol)

## Description

`null(A)` returns a matrix whose columns are an orthonormal basis of the vectors `x` with `A*x = 0`, from the singular value decomposition. Singular values at or below `max(size(A)) * eps(max(s))` count as zero; `tol` sets that threshold. A full-rank `A` gives an empty `n`-by-0 matrix.

The basis is unique only up to sign and rotation, so the signs may differ from MATLAB's. Evans does not support the rational basis `null(A, 'r')`.

## Example

```matlab
A = [1 1 1; 1 2 3];
Z = null(A)
A*Z
```

## See also

[orth](orth) · [svd](svd) · [pinv](pinv)
