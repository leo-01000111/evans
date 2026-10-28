# expm

Matrix exponential.

## Syntax

    Y = expm(A)

## Description

`expm(A)` is `I + A + A^2/2! + A^3/3! + ...` for a square matrix `A`, computed by scaling and squaring with a Padé approximation. It is not `exp(A)`, which takes the exponential of each element. The state transition matrix of `x' = A*x` is `expm(A*t)`.

## Example

```matlab
A = [0 1; -2 -3];
Phi = expm(A*0.5)
```

## See also

[logm](logm) · [sqrtm](sqrtm) · [exp](exp) · [eig](eig)
