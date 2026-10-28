# svd

Singular value decomposition.

## Syntax

    s = svd(A)
    [U, S, V] = svd(A)
    [U, S, V] = svd(A, 'econ')
    [U, S, V] = svd(A, 0)
    [U, S, V] = svd(..., 'vector')

## Description

`svd(A)` returns the singular values of `A` as a column, largest first. `[U, S, V] = svd(A)` gives unitary `U` and `V` and a diagonal `S` (the size of `A`) with `A = U*S*V'`.

`'econ'` gives the economy size: for an `m`-by-`n` `A`, `U` is `m`-by-`k`, `S` `k`-by-`k`, `V` `n`-by-`k`, `k = min(m, n)`. `svd(A, 0)` economises only when `m > n`. `'vector'` returns `S` as a column, `'matrix'` as a matrix.

The signs of the singular vectors may differ from MATLAB's; any pair `u, v` can be negated together.

## Example

```matlab
A = [1 2; 3 4; 5 6];
s = svd(A)
[U, S, V] = svd(A, 'econ');
norm(U*S*V' - A)
```

## See also

[qr](qr) · [pinv](pinv) · [null](null) · [orth](orth) · [cond](cond) · [eig](eig)
