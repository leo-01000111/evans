# gmres

Generalised minimal residual method for a square system.

## Syntax

    x = gmres(A, b)
    [x, flag, relres, iter, resvec] = gmres(A, b, restart, tol, maxit, M1, M2, x0)

## Description

Solves `A*x = b` for a general matrix. `restart` empty means full GMRES. `iter` is `[outer inner]`, as in MATLAB. See [pcg](pcg) for the other arguments.

## Example

```matlab
A = sparse([4 1 0; 1 3 1; 0 1 2]);
b = [1; 2; 3];
x = gmres(A, b, [], 1e-10, 3);
norm(A*x - b) < 1e-8
```

## See also

[pcg](pcg) · [bicgstab](bicgstab)
