# spalloc

Sparse matrix of zeros, with room reserved.

## Syntax

    S = spalloc(m, n, nz)

## Description

An m-by-n all-zero sparse matrix. `nz` is MATLAB's storage hint; Evans grows the matrix as needed and ignores it.

## Example

```matlab
S = spalloc(3, 3, 3);
S(2, 2) = 7;
nnz(S)
```

## See also

[sparse](sparse) · [nzmax](nzmax)
