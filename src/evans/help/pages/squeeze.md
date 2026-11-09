# squeeze

Remove dimensions of size 1.

## Syntax

    B = squeeze(A)

## Description

`squeeze` drops every singleton dimension of an N-D array, so a 1-by-1-by-5 array becomes a 5-by-1 column and a 2-by-1-by-3 array becomes 2-by-3. A matrix is returned as it is. It is how you pull a vector out of an N-D array: `squeeze(A(1, 2, :))` is the vector of values along the third dimension.

## Example

```matlab
A = reshape(1:24, 2, 3, 4);
v = squeeze(A(1, 2, :))
```

## See also

[permute](permute) · [reshape](reshape) · [size](size)
