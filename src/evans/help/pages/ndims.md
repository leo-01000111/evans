# ndims

Number of dimensions of an array.

## Syntax

    n = ndims(A)

## Description

Always at least 2. A 2-by-3-by-4 array has `ndims` 3; trailing dimensions of size 1 do not count, so `ndims(zeros(2, 3, 1))` is 2.

## Example

```matlab
A = zeros(2, 3, 4);
n = ndims(A)
```

## See also

[size](size) · [numel](numel) · [length](length)
