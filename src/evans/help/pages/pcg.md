# pcg

Preconditioned conjugate gradients for a symmetric positive definite system.

## Syntax

    x = pcg(A, b)
    [x, flag, relres, iter, resvec] = pcg(A, b, tol, maxit, M1, M2, x0)

## Description

Solves `A*x = b`. Defaults: `tol = 1e-6`, `maxit = min(n, 20)`. The preconditioner is `M = M1*M2` (matrices; `M1`, `M2` may be sparse). `flag` is 0 when the tolerance is met, 1 when `maxit` ran out. Without a `flag` output a one-line message says how it ended. `A` must be a matrix: function handles are not supported yet.

## Example

```matlab
n = 50; e = ones(n, 1);
K = spdiags([-e 2*e -e], -1:1, n, n);
b = K * e;
[x, flag, relres, iter] = pcg(K, b, 1e-10, 200);
flag
norm(x - e) < 1e-6
```

## See also

[gmres](gmres) · [bicgstab](bicgstab) · [minres](minres) · [spdiags](spdiags)
