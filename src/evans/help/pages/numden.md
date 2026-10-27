# numden

Numerator and denominator of a symbolic expression.

## Syntax

    [N, D] = numden(f)

## Description

`[N, D] = numden(f)` puts `f` over a common denominator, cancels any factor the two share, and returns the numerator and denominator as polynomials, so `f = N/D` with `N` and `D` coprime. A sum of fractions is combined first: `1/s + 1/(s + 1)` gives `N = 2*s + 1` and `D = s^2 + s`.

With [sym2poly](sym2poly) this is how a formula becomes a transfer function: `tf(sym2poly(N), sym2poly(D))`. A matrix gives matrices of numerators and denominators, element by element.

## Example

```matlab
syms s
A = [0 1; -2 -3];  B = [0; 1];  C = [1 0];
T = C*inv(s*eye(2) - A)*B;
[N, D] = numden(T)
G = tf(sym2poly(N), sym2poly(D))
```

## See also

[sym2poly](sym2poly) · [tf](tf) · [partfrac](partfrac) · [simplify](simplify)
