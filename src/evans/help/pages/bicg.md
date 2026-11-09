# bicg

Biconjugate gradients.

## Syntax

    x = bicg(A, b)
    [x, flag, relres, iter, resvec] = bicg(A, b, tol, maxit, M1, M2, x0)

## Description

For a general square `A`. Arguments and outputs as for [pcg](pcg).

## Example

```matlab
A = sparse([4 1 0; 1 3 1; 0 1 2]);
[x, flag] = bicg(A, [1; 2; 3], 1e-10, 50);
flag
```

## See also

[pcg](pcg) · [bicgstab](bicgstab)
