# polyder

Differentiate a polynomial, a product or a quotient of two.

## Syntax

    k = polyder(p)
    k = polyder(a, b)
    [q, d] = polyder(b, a)

## Description

Polynomials are coefficient vectors, highest power first, as [polyval](polyval) takes them. `polyder(p)` is the derivative of `p`; `polyder(a, b)` that of the product `a*b`; and with two outputs, `q./d` is the derivative of the quotient `b/a`.

## Example

```matlab
polyder([1 0 -3 2])
[q, d] = polyder([1 0], [1 1])
```

## See also

[polyint](polyint) · [polyval](polyval) · [conv](conv)
