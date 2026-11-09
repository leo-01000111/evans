# issparse

Whether a value is a sparse matrix.

## Syntax

    tf = issparse(A)

## Description

True for a matrix made by `sparse` or one of the operations that keeps sparsity, false for anything else.

## Example

```matlab
issparse(speye(3))
issparse(eye(3))
issparse(speye(3) * ones(3))
```

## See also

[sparse](sparse) · [full](full)
