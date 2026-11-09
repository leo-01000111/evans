# nonzeros

The nonzero elements as a column.

## Syntax

    v = nonzeros(A)

## Description

Column by column, the way MATLAB lists them.

## Example

```matlab
A = sparse([1 2 2], [1 1 2], [4 5 6]);
nonzeros(A)'
```

## See also

[nnz](nnz) · [find](find)
