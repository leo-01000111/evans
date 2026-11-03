# intlinprog

Solve a linear programme where some variables are integers.

## Syntax

    x = intlinprog(f, intcon, A, b)
    x = intlinprog(f, intcon, A, b, Aeq, beq)
    x = intlinprog(f, intcon, A, b, Aeq, beq, lb, ub)
    [x, fval, exitflag, output] = intlinprog(...)

## Description

Minimises `f'*x` subject to `A*x <= b`, `Aeq*x = beq` and `lb <= x <= ub`, with the variables listed in `intcon` taking integer values. Pass `[]` for constraints that are absent.

Evans solves it with HiGHS's branch and bound, through SciPy's `milp`.

## Example

```matlab
f = [-1; -2];
A = [1 1; 1 -1];  b = [4.5; 1];
x = intlinprog(f, [1 2], A, b, [], [], [0; 0], [])
```

## See also

[linprog](linprog) · [quadprog](quadprog)
