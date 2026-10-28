# sqrtm

Matrix square root.

## Syntax

    X = sqrtm(A)

## Description

`sqrtm(A)` returns the principal square root `X` of a square matrix, with `X*X = A`. It is not `sqrt(A)`, which works element by element. A matrix with negative eigenvalues has a complex square root.

Evans does not warn, as MATLAB does, when `A` is singular and the root may be inaccurate.

## Example

```matlab
A = [4 1; 0 9];
X = sqrtm(A)
X*X
```

## See also

[expm](expm) · [logm](logm) · [sqrt](sqrt) · [chol](chol)
