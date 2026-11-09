# nzmax

Storage allocated for nonzeros.

## Syntax

    n = nzmax(A)

## Description

For a sparse matrix, the number of stored entries; for a full one, `numel(A)`.

## Example

```matlab
nzmax(speye(5))
```

## See also

[nnz](nnz) · [spalloc](spalloc)
