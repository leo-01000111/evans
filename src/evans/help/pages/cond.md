# cond

Condition number of a matrix.

## Syntax

    c = cond(A)
    c = cond(A, p)

## Description

`cond(A)` is the 2-norm condition number, the ratio of the largest to the smallest singular value; it works for rectangular matrices too. A singular matrix gives `Inf`. Large values mean a linear system with `A` loses accuracy.

`cond(A, p)` with `p` = `1`, `Inf` or `'fro'` is `norm(A, p) * norm(inv(A), p)` for a square `A`.

## Example

```matlab
cond([1 2; 3 4])
cond([1 2; 3 4], 1)
```

## See also

[svd](svd) · [inv](inv) · [det](det)
