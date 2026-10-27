# fplot

Plot a symbolic expression or a function over an interval.

## Syntax

    fplot(f)
    fplot(f, [a b])
    fplot(f, [a b], LineSpec)

## Description

`fplot(f)` draws `f` over `[-5 5]`, and `fplot(f, [a b])` over `[a b]`. `f` is a symbolic expression of one variable, or a function handle that accepts an array, such as `@(t) exp(-t).*sin(t)`. A line spec such as `'r--'` styles the line as in [plot](plot), and [hold](hold), [title](title) and the other figure commands work as usual.

The curve is sampled at 600 points; for a fast oscillation over a long interval, plot a shorter one. An expression with more than one variable needs [subs](subs) first.

## Example

```matlab
syms t
fplot(exp(-t)*sin(3*t), [0 5])
title('A decaying oscillation')
```

## See also

[plot](plot) · [matlabFunction](matlabFunction) · [ilaplace](ilaplace)
