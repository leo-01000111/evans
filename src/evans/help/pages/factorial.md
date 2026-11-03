# factorial

Factorial of a nonnegative integer.

## Syntax

    f = factorial(n)

## Description

`n!` for each element of `n`. From 171 up the result is Inf, as a double cannot hold it; for ratios of large factorials use [nchoosek](nchoosek) or [gammaln](gammaln).

## Example

```matlab
factorial(5)
factorial([0 1 2 3])
```

## See also

[nchoosek](nchoosek) · [gamma](gamma) · [gammaln](gammaln)
