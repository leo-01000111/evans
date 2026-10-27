# laplace

Laplace transform of a symbolic expression.

## Syntax

    F = laplace(f)
    F = laplace(f, transVar)
    F = laplace(f, var, transVar)

## Description

`laplace(f)` is the one-sided Laplace transform of `f`, the integral of `f(t)*exp(-s*t)` from 0 to infinity. By default `f` is a function of `t` and the result a function of `s`. If `f` has no `t`, its variable is the one closest to `x` alphabetically, and if that is `s` the result is in `z`.

`laplace(f, transVar)` names the result's variable, and `laplace(f, var, transVar)` names both.

The unit step and the impulse are `heaviside(t)` and `dirac(t)`, so a delayed step is `heaviside(t - 2)` and transforms to `exp(-2*s)/s`. A parameter with an assumption keeps the result tidy: with `syms a positive`, `laplace(exp(-a*t))` is `1/(a + s)`.

A matrix is transformed element by element. When no closed form is found, the result is written as `laplace(f, t, s)`.

## Example

```matlab
syms t s
laplace(t^2*exp(-3*t))
laplace(heaviside(t - 2))
F = laplace(exp(-t)*cos(2*t))
```

## See also

[ilaplace](ilaplace) · [syms](syms) · [partfrac](partfrac) · [simplify](simplify)
