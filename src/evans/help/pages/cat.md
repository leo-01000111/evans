# cat

Join arrays along any dimension.

## Syntax

    C = cat(dim, A, B, ...)

## Description

`cat(1, A, B)` stacks vertically, the same as `[A; B]`. `cat(2, A, B)` joins side by side, the same as `[A, B]`. `cat(3, A, B)` stacks the arrays as pages of an N-D array: two 2-by-2 matrices give a 2-by-2-by-2 array. The sizes must agree in every dimension but `dim`, or it stops with "Dimensions of arrays being concatenated are not consistent."

From the third dimension up, `cat` joins numeric, logical and cell arrays. For cells, `cat(3, {1, 2}, {3, 4})` is a 1-by-2-by-2 cell array.

## Example

```matlab
P = cat(3, [1 2; 3 4], [5 6; 7 8]);
size(P)
P(:, :, 2)
```

## See also

[permute](permute) · [squeeze](squeeze) · [reshape](reshape) · [repmat](repmat)
