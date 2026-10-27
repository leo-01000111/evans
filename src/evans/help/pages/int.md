# int

Integral of a symbolic expression, indefinite or definite.

## Syntax

    F = int(f)
    F = int(f, x)
    F = int(f, a, b)
    F = int(f, x, a, b)

## Description

`int(f)` is an antiderivative of `f` with respect to its default variable (the one closest to `x` alphabetically), without a constant of integration. `int(f, x)` names the variable.

`int(f, a, b)` and `int(f, x, a, b)` integrate from `a` to `b`. The bounds may be numbers, `Inf`, or expressions. An integral with no closed form is returned unevaluated, as `int(f, x)`; [double](double) of a definite one then evaluates it numerically.

The definite form gives the classical performance indices directly, such as the integral of the squared error of a step response.

## Example

```matlab
syms t
int(t*exp(-t))
e = exp(-t)*cos(2*t);
ISE = int(e^2, t, 0, Inf)
```

## See also

[diff](diff) · [limit](limit) · [laplace](laplace) · [double](double)
