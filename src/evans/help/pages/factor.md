# factor

Factor a symbolic polynomial, or split a number into its prime factors.

## Syntax

    g = factor(f)
    g = factor(f, x)
    p = factor(n)

## Description

`factor(f)` writes a symbolic polynomial, or a ratio of polynomials, as a product of irreducible factors over the rationals: `s^2 + 3*s + 2` becomes `(s + 1)*(s + 2)`. A factor with irrational roots, such as `s^2 - 2`, is left whole. With a variable, `factor(f, x)` factors in that variable only.

For poles and zeros as numbers, [roots](roots) of the coefficients is the numeric route.

`factor(n)` of a positive integer is the row of its prime factors in increasing order, so `factor(84)` is `[2 2 3 7]`.

## Example

```matlab
syms s
factor(s^3 + 6*s^2 + 11*s + 6)
factor(84)
```

## See also

[expand](expand) · [partfrac](partfrac) · [roots](roots) · [simplify](simplify)
