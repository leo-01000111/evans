# spones

Replace the nonzeros of a matrix with ones.

## Syntax

    R = spones(S)

## Description

Same pattern as `S`, every stored entry set to 1. Handy for plotting or counting structure.

## Example

```matlab
S = sparse([1 2], [2 3], [5 -2], 3, 3);
full(spones(S))
```

## See also

[sparse](sparse) · [nnz](nnz)
