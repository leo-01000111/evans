# cross

Cross product of 3-element vectors.

## Syntax

    C = cross(A, B)
    C = cross(A, B, dim)

## Description

`cross(A, B)` of two 3-element vectors is their cross product, a row if both are rows and a column otherwise. For matrices of the same size, it takes the cross product along the first dimension of length 3 (the columns of a 3-by-n matrix); `dim` picks the dimension.

Both inputs must have length 3 along that dimension.

## Example

```matlab
cross([1 0 0], [0 1 0])
cross([1;2;3], [4;5;6])
```

## See also

[dot](dot) · [det](det)
