# fmincon

Minimise a function subject to constraints.

## Syntax

    x = fmincon(fun, x0, A, b)
    x = fmincon(fun, x0, A, b, Aeq, beq, lb, ub)
    x = fmincon(fun, x0, A, b, Aeq, beq, lb, ub, nonlcon, options)
    [x, fval, exitflag, output] = fmincon(...)

## Description

The constraints are `A*x <= b`, `Aeq*x = beq`, `lb <= x <= ub`, and `[c, ceq] = nonlcon(x)` with `c <= 0` and `ceq = 0`. Pass `[]` for any you don't use. `nonlcon` must be a function with two outputs.

Evans solves with sequential quadratic programming, where MATLAB's default is interior-point; on a well-posed problem both reach the same local minimum. The `lambda`, `grad` and `hessian` outputs are not supported.

## Example

```matlab
f = @(x) (x(1) - 2)^2 + (x(2) - 1)^2;
x = fmincon(f, [0; 0], [1 1], 2)
```

## See also

[linprog](linprog)
