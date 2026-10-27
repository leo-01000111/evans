# subs

Substitute values or expressions for variables in a symbolic expression.

## Syntax

    g = subs(f, old, new)
    g = subs(f, new)
    g = subs(f)

## Description

`subs(f, old, new)` replaces the variable `old` by `new`, which may be a number, another expression, or an array of numbers to get an array back. `old` may also be the variable's name as text. Several at once are given as cells, `subs(f, {s, K}, {1i, 5})`, and are replaced together, so swapping two variables works.

`subs(f, new)` replaces the default variable, the one closest to `x` alphabetically. `subs(f)` replaces every variable that has a value in the workspace: after `K = 2`, `subs(K/(s + 1))` is `2/(s + 1)`.

The result is still symbolic, even when no variable is left; [double](double) turns it into a number. Evaluating a transfer function at a point is `subs(G, s, 1i*w)`; for many points, [matlabFunction](matlabFunction) is faster.

## Example

```matlab
syms s K
L = K/(s*(s + 2));
T = simplify(L/(1 + L))
subs(T, K, 4)
double(subs(T, {s, K}, {0.5, 4}))
```

## See also

[double](double) · [matlabFunction](matlabFunction) · [simplify](simplify) · [solve](solve)
