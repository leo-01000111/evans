# double

Convert to a number.

## Syntax

    y = double(x)

## Description

`double(x)` of a symbolic value with no variables left gives its value as an ordinary number, or a numeric array for a symbolic matrix: `double(sym(pi))` is 3.1416, and a complex result stays complex. An expression that still has a variable is an error; substitute values for the variables first with [subs](subs).

`double` of a number returns it unchanged, `double(true)` is 1, and `double('A')` gives the character codes. Of an integer or `single` value it gives the same number as a plain double, so `double(int8(5)) / 2` is 2.5, not 3.

## Example

```matlab
syms s
G = 10/(s^2 + 2*s + 10);
g = subs(G, s, 2i)
abs(double(g))
```

## See also

[subs](subs) · [sym](sym) · [matlabFunction](matlabFunction) · [single](single) · [int8](int8) · [cast](cast)
