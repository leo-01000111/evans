# syms

Make symbolic variables, so formulas are kept as formulas instead of being worked out as numbers.

## Syntax

    syms x
    syms s t
    syms a positive
    syms x real
    syms

## Description

`syms s t` creates the symbolic variables `s` and `t` in the workspace. From then on `+`, `-`, `*`, `/`, `^` and the elementary functions (`exp`, `sin`, `sqrt`, `abs`…) build exact formulas: `1/(s^2 + 2*s + 1)` stays a ratio of polynomials, and `sqrt(2)` stays `sqrt(2)`.

A word after the names is an assumption on every one of them: `real`, `positive`, `integer` or `rational`. Assumptions let [simplify](simplify) and [solve](solve) go further: with `syms a positive`, `sqrt(a^2)` simplifies to `a`.

`syms` on its own prints the names of the symbolic variables in the workspace.

At the Evans console `s` starts out as the transfer function `tf('s')`. `syms s` replaces it with a symbol, and the two do not mix: a formula in a symbolic `s` is not a model. Turn one into a model with [numden](numden) and [sym2poly](sym2poly), and type `s = tf('s')` to get the transfer function back.

Evans does not support symbolic functions such as `syms y(t)`, so `dsolve` is not available either; solve a linear differential equation with [laplace](laplace) and [ilaplace](ilaplace) instead. Numbers that meet a symbol are made exact, as MATLAB does: `0.1*s` is `s/10`.

## Example

```matlab
syms s t
F = laplace(exp(-2*t)*sin(3*t))
f = ilaplace(1/(s*(s + 1)))
```

```matlab
syms a positive
simplify(sqrt(a^2))
```

## See also

[sym](sym) · [laplace](laplace) · [simplify](simplify) · [subs](subs) · [s](s)
