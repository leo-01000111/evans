# permute

Rearrange the dimensions of an array.

## Syntax

    B = permute(A, order)

## Description

`order` lists the dimensions of `A` in the order they take in `B`. For a matrix, `permute(A, [2 1])` is the transpose. For a 2-by-3-by-4 array, `permute(A, [3 1 2])` is 4-by-2-by-3, and `B(k, i, j)` equals `A(i, j, k)`. `order` must name every dimension once, and may be longer than `ndims(A)` to add trailing dimensions of size 1.

Matrix transpose `A'` is not defined for N-D arrays; use `permute`. Cell arrays can be permuted too.

## Example

```matlab
A = reshape(1:24, 2, 3, 4);
B = permute(A, [3 1 2]);
size(B)
B(4, 2, 3)
```

## See also

[squeeze](squeeze) · [cat](cat) · [reshape](reshape) · [size](size)
