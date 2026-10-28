# pinv

Moore-Penrose pseudo-inverse.

## Syntax

    B = pinv(A)
    B = pinv(A, tol)

## Description

`pinv(A)` is computed from the singular value decomposition, inverting the singular values above a tolerance and dropping the rest. It works for rectangular and singular matrices; `pinv(A)*b` is the minimum-norm least-squares solution of `A*x = b`.

The default tolerance is `max(size(A)) * eps(norm(A))`, as in MATLAB; `tol` sets it.

## Example

```matlab
A = [1 2; 2 4; 3 6];
B = pinv(A)
```

## See also

[inv](inv) · [svd](svd) · [null](null) · [regress](regress)
