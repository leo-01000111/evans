# circshift

Shift the elements of an array round in a circle.

## Syntax

    B = circshift(A, k)
    B = circshift(A, k, dim)
    B = circshift(A, [r c])

## Description

`circshift(A, k)` moves the elements `k` places along the first dimension whose size is not 1, so a row vector shifts along the row and a matrix shifts its rows down; those pushed off the end come back at the start. A negative `k` shifts the other way.

`circshift(A, k, dim)` shifts along dimension `dim`. `circshift(A, [r c])` shifts by `r` rows and `c` columns. A char vector works too.

## Example

```matlab
circshift([1 2 3 4 5], 2)
circshift([1 2; 3 4; 5 6], 1)
circshift([1 2; 3 4; 5 6], 1, 2)
```

## See also

[reshape](reshape) · [sort](sort) · [repmat](repmat)
