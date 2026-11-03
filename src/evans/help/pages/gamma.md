# gamma

Gamma function.

## Syntax

    y = gamma(x)

## Description

Γ(x) elementwise; Γ(n) = (n−1)! at positive integers. It is Inf at 0 and at the negative integers, as in MATLAB, and overflows to Inf above about 171.

## Example

```matlab
gamma([1 2 3 4 0.5])
sqrt(pi)
```

## See also

[gammaln](gammaln) · [factorial](factorial) · [beta](beta)
