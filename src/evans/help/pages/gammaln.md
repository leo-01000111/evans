# gammaln

Logarithm of the gamma function.

## Syntax

    y = gammaln(x)

## Description

log Γ(x) for nonnegative `x`, without forming Γ(x): it stays finite where `gamma` overflows.

## Example

```matlab
gammaln(200)
log(gamma(200))
```

## See also

[gamma](gamma) · [betaln](betaln)
