# speye

Sparse identity matrix.

## Syntax

    S = speye(n)
    S = speye(m, n)

## Description

A sparse matrix with ones on the main diagonal. Use it for `A + sigma*speye(n)` shifts and as a preconditioner start.

## Example

```matlab
I = speye(4);
full(I)
issparse(I)
```

## See also

[sparse](sparse) · [eye](eye) · [spones](spones)
