# ilaplace

Inverse Laplace transform of a symbolic expression.

## Syntax

    f = ilaplace(F)
    f = ilaplace(F, transVar)
    f = ilaplace(F, var, transVar)

## Description

`ilaplace(F)` returns the time function whose Laplace transform is `F`. By default `F` is a function of `s` and the result a function of `t`; if `F` is itself a function of `t`, the result is in `x`. The other forms name the variables, as for [laplace](laplace).

The result is for `t > 0`, written the way MATLAB writes it: `ilaplace(1/(s + 1))` is `exp(-t)`, without a `heaviside(t)` factor. A delay such as `exp(-2*s)` does give a `heaviside(t - 2)`.

This is the hand method for a response: multiply the transfer function by the input's transform and invert. The step response of `G` is `ilaplace(G/s)`. [matlabFunction](matlabFunction) turns the formula into a function to plot or compare with [step](step).

## Example

```matlab
syms s t
y = ilaplace(4/(s*(s^2 + 2*s + 4)))
fplot(y, [0 6])
```

```matlab
syms s
ilaplace((s + 3)/((s + 1)*(s + 2)))
```

## See also

[laplace](laplace) · [partfrac](partfrac) · [fplot](fplot) · [step](step)
