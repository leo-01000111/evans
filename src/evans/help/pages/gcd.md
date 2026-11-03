# gcd

Greatest common divisor.

## Syntax

    g = gcd(a, b)
    [g, u, v] = gcd(a, b)

## Description

The greatest common divisor of integers `a` and `b`, elementwise. With three outputs, `u` and `v` satisfy `a*u + b*v = g` (Bézout's identity).

## Example

```matlab
gcd(12, 18)
[g, u, v] = gcd(240, 46)
```

## See also

[lcm](lcm) · [isprime](isprime)
