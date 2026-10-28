# logm

Matrix logarithm.

## Syntax

    L = logm(A)

## Description

`logm(A)` is the principal matrix logarithm of a square matrix, the inverse of [expm](expm): `expm(logm(A))` is `A`. It is not `log(A)`, which works element by element. A matrix with eigenvalues on the negative real axis has a complex logarithm.

Evans does not warn, as MATLAB does, when the result may be inaccurate.

## Example

```matlab
A = [1 1; 0 1];
L = logm(A)
expm(L)
```

## See also

[expm](expm) · [sqrtm](sqrtm)
