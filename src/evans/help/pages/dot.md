# dot

Dot product of two vectors, or of the columns of two matrices.

## Syntax

    d = dot(A, B)
    d = dot(A, B, dim)

## Description

`dot(A, B)` of two vectors with the same number of elements (either orientation) is `sum(conj(A).*B)`: for complex vectors it conjugates the first. For matrices of the same size it works down each column and returns a row; `dim` picks the dimension.

## Example

```matlab
dot([1 2 3], [4 5 6])
dot([1 2; 3 4], [1 2; 3 4])
```

## See also

[cross](cross) · [sum](sum) · [abs](abs)
