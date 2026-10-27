# solve

Solve symbolic equations for their variables.

## Syntax

    S = solve(eqn, x)
    S = solve(eqn)
    S = solve(eqn1, eqn2, x, y)
    [x, y] = solve(eqn1, eqn2, x, y)

## Description

An equation is written with `==`, as in `x^2 + 2*x == 3`; an expression without `==` means that it equals zero. `solve(eqn, x)` returns the solutions for `x`: one value, or a column of them. Without `x`, the variable is the one closest to `x` alphabetically.

For several equations and unknowns, give the equations and then the variables. With one output the answer is a struct with a field for each variable, `S.a`, `S.b`; with as many outputs as variables, each gets its own. Without variables, as many are chosen as there are equations, and returned in alphabetical order.

Name-value options such as `'Real', true` are accepted and ignored. An equation with no solution gives an empty result.

A use from design: match a closed loop's characteristic polynomial to a desired one, coefficient by coefficient, and solve for the gains.

## Example

```matlab
syms x
solve(x^2 + 2*x == 3, x)
```

```matlab
syms s k1 k2
p = expand(s*(s + 1) + k2*s + k1)
target = expand((s + 2)^2)
[K1, K2] = solve(k1 == 4, 1 + k2 == 4, k1, k2)
```

## See also

[subs](subs) · [syms](syms) · [roots](roots) · [place](place)
