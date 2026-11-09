# nnz

Number of nonzero elements.

## Syntax

    n = nnz(A)

## Description

Works on sparse and full matrices; stored zeros do not count.

## Example

```matlab
A = sparse([1 2 3], [1 2 3], [1 0 5]);
nnz(A)
nnz([1 0 2; 0 0 3])
```

## See also

[nonzeros](nonzeros) · [nzmax](nzmax) · [find](find)
