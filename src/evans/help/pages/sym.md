# sym

A symbolic variable from a name, or a number made exact.

## Syntax

    x = sym('x')
    x = sym('x', 'real')
    c = sym(number)
    A = sym('a', [m n])

## Description

`sym('x')` returns the symbolic variable `x` without putting it in the workspace under that name, so `y = sym('x')` is allowed. A second argument such as `'real'` or `'positive'` is an assumption, as for [syms](syms).

`sym(number)` gives the exact number a double stands for: `sym(0.1)` is `1/10`, `sym(1/3)` is `1/3`, `sym(pi)` is `pi` and `sym(sqrt(2))` is `sqrt(2)`. A number with no short exact form is taken as the decimal it prints as. `sym` of a matrix converts every element.

`sym('a', [1 3])` is the row `[a1, a2, a3]`, and `sym('K', [2 2])` the matrix of `K1_1` to `K2_2`: handy for a gain matrix to solve for.

To read a whole formula from text, use `str2sym('s^2 + 2*s + 1')`.

## Example

```matlab
c = sym(1/3) + sym(1/6)
K = sym('k', [1 2])
x = sym('x');
expand((x + c)^2)
```

## See also

[syms](syms) · [double](double) · [solve](solve)
