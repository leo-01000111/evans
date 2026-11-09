# minres

Minimum residual method for a symmetric system.

## Syntax

    x = minres(A, b)
    [x, flag, relres, iter, resvec] = minres(A, b, tol, maxit, M1, M2, x0)

## Description

For symmetric `A`, definite or not. Arguments and outputs as for [pcg](pcg).

## Example

```matlab
A = sparse([2 -1 0; -1 2 -1; 0 -1 2]);
[x, flag] = minres(A, [1; 0; 1], 1e-10, 50);
flag
```

## See also

[pcg](pcg) · [gmres](gmres)
