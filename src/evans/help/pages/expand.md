# expand

Multiply out products and powers in a symbolic expression.

## Syntax

    g = expand(f)

## Description

`expand(f)` distributes products over sums and expands integer powers: `(s + 1)^3` becomes `s^3 + 3*s^2 + 3*s + 1`. Functions of sums are expanded too where there is an identity for it, so `exp(a + b)` becomes `exp(a)*exp(b)`.

It is the step before reading off polynomial coefficients by eye, and the opposite of [factor](factor). [sym2poly](sym2poly) expands by itself, so there is no need to call `expand` before it.

## Example

```matlab
syms s K
expand((s + 1)*(s + 2)*(s + K))
```

## See also

[factor](factor) · [simplify](simplify) · [sym2poly](sym2poly)
