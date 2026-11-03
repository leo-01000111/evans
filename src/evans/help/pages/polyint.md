# polyint

Integrate a polynomial.

## Syntax

    q = polyint(p)
    q = polyint(p, k)

## Description

Returns the coefficients of the integral of `p`, with the constant of integration `k` (0 by default) as its last coefficient.

## Example

```matlab
q = polyint([3 2 1])
diff(polyval(q, [0 1]))
```

## See also

[polyder](polyder) · [polyval](polyval) · [integral](integral)
