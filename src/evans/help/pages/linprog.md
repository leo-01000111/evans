# linprog

Linear programming: minimise f'*x subject to linear constraints.

## Syntax

    x = linprog(f, A, b)
    x = linprog(f, A, b, Aeq, beq, lb, ub)
    [x, fval, exitflag, output] = linprog(...)

## Description

`linprog` minimises `f'*x` with `A*x <= b`, `Aeq*x = beq` and `lb <= x <= ub`, using the HiGHS solver. `x` is a column. `exitflag` is 1 at an optimum, `-2` when no point satisfies the constraints and `-3` when the problem is unbounded.

## Example

```matlab
f = [-1; -2];
A = [1 1; 1 -1];
b = [4; 2];
x = linprog(f, A, b, [], [], [0; 0], [])
```

## See also

[fmincon](fmincon)
