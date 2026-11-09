# full

Convert a sparse matrix to a full one.

## Syntax

    A = full(S)

## Description

A full matrix or number is returned unchanged.

## Example

```matlab
S = speye(3) * 2;
A = full(S)
```

## See also

[sparse](sparse) · [issparse](issparse)
