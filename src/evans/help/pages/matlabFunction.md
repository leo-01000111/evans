# matlabFunction

Turn a symbolic expression into a function handle that evaluates it on numbers.

## Syntax

    h = matlabFunction(f)
    h = matlabFunction(f, 'Vars', {t, a})

## Description

`h = matlabFunction(f)` returns a function whose inputs are the variables of `f` in alphabetical order, and which computes `f` on numbers. It works elementwise on arrays, so `h(t)` with a time vector gives the whole curve at once: much faster than calling [subs](subs) point by point. `'Vars'` sets the inputs and their order.

The usual use is to compare a hand derivation with the numeric answer: invert a transform with [ilaplace](ilaplace), evaluate it on a grid, and plot it beside [step](step).

## Example

```matlab
syms s t
y = ilaplace(1/(s*(s + 1)));
h = matlabFunction(y);
tt = linspace(0, 5, 6);
h(tt)
```

## See also

[subs](subs) · [fplot](fplot) · [ilaplace](ilaplace) · [double](double)
