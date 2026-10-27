# sym2poly

Coefficients of a symbolic polynomial, as numbers.

## Syntax

    c = sym2poly(p)
    p = poly2sym(c, x)

## Description

`sym2poly(p)` returns the coefficients of the polynomial `p`, highest power first, as an ordinary row of numbers: the form [tf](tf), [roots](roots) and [polyval](polyval) take. `p` is expanded first, so `(s + 1)^2` gives `[1 2 1]`. It must be a polynomial in one variable with numeric coefficients; use [subs](subs) to give values to the others, and [numden](numden) to split a ratio.

`poly2sym(c, x)` goes the other way, building the polynomial in `x` from the coefficients `c`; without `x` the variable is `x`.

## Example

```matlab
syms s
p = expand((s + 1)*(s + 2)*(s + 3));
c = sym2poly(p)
roots(c)
poly2sym([1 0 -4], s)
```

## See also

[numden](numden) · [tf](tf) · [roots](roots) · [poly](poly)
