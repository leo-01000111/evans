# partfrac

Partial-fraction expansion of a symbolic ratio of polynomials.

## Syntax

    g = partfrac(f)
    g = partfrac(f, x)

## Description

`partfrac(f)` splits a rational function into a sum of simple fractions, one for each factor of the denominator, with repeated factors giving one term per power: the form a transform table can be read against before inverting by hand. The variable defaults to the one closest to `x` alphabetically; give it as the second argument otherwise.

Denominators are factored over the rationals, so a quadratic with complex roots stays as one term.

[ilaplace](ilaplace) does the whole inversion at once; `partfrac` shows the steps in between. For the poles as numbers, use [roots](roots) of the denominator's coefficients.

## Example

```matlab
syms s
F = partfrac(1/(s*(s + 1)*(s + 2)))
partfrac((s + 3)/((s + 1)^2*(s + 2)))
```

## See also

[ilaplace](ilaplace) · [factor](factor) · [numden](numden)
