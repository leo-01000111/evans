# quadprog

Minimise a quadratic function under linear constraints.

## Syntax

    x = quadprog(H, f)
    x = quadprog(H, f, A, b)
    x = quadprog(H, f, A, b, Aeq, beq, lb, ub)
    [x, fval, exitflag, output, lambda] = quadprog(...)

## Description

Minimises `0.5*x'*H*x + f'*x` subject to `A*x <= b`, `Aeq*x = beq` and `lb <= x <= ub`. `lambda` holds the Lagrange multipliers, in MATLAB's fields `ineqlin`, `eqlin`, `lower` and `upper`.

Like MATLAB's default algorithm, Evans solves convex problems only: `H` must be positive semi-definite.

## Example

```matlab
H = [1 -1; -1 2];  f = [-2; -6];
A = [1 1; -1 2; 2 1];  b = [2; 2; 3];
[x, fval] = quadprog(H, f, A, b, [], [], [0; 0], [])
```

## See also

[linprog](linprog) · [fmincon](fmincon) · [intlinprog](intlinprog)
