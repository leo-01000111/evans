# sparse

Create a sparse matrix, or convert a full one.

## Syntax

    S = sparse(A)
    S = sparse(m, n)
    S = sparse(i, j, v)
    S = sparse(i, j, v, m, n)

## Description

`sparse(A)` stores only the nonzeros of `A`. `sparse(i, j, v, m, n)` puts `v(k)` at row `i(k)`, column `j(k)` of an m-by-n matrix; entries that repeat a position are added, as in MATLAB. `sparse(m, n)` is all zeros. Sparse matrices are a type of their own in Evans: `+ - .* * \ /`, the transpose, indexing, assignment and `[A B; C D]` keep them sparse where MATLAB does. Other functions are given `full(A)`.

A single element, `S(i, j)`, comes back as a plain number rather than a 1-by-1 sparse matrix, and a loop of `S(i, j) = v` is slow: build with `sparse(i, j, v)` instead.

## Example

```matlab
S = sparse([1 2 3], [1 2 3], [4 5 6])
nnz(S)
full(S)
```

## See also

[speye](speye) · [full](full) · [nnz](nnz) · [spalloc](spalloc) · [spdiags](spdiags) · [issparse](issparse)
