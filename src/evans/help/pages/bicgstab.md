# bicgstab

Stabilised biconjugate gradients.

## Syntax

    x = bicgstab(A, b)
    [x, flag, relres, iter, resvec] = bicgstab(A, b, tol, maxit, M1, M2, x0)

## Description

For a general square `A`. Arguments and outputs as for [pcg](pcg).

## Example

```matlab
A = sparse([4 1 0; 1 3 1; 0 1 2]);
[x, flag] = bicgstab(A, [1; 2; 3], 1e-10, 50);
flag
```

## See also

[pcg](pcg) · [gmres](gmres) · [bicg](bicg)
