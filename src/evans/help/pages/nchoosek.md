# nchoosek

Binomial coefficient, or all combinations of a vector's elements.

## Syntax

    c = nchoosek(n, k)
    C = nchoosek(v, k)

## Description

`nchoosek(n, k)` for scalars is the number of ways to choose `k` of `n`, `n!/(k!(n-k)!)`. For a vector `v` it returns a matrix whose rows are every combination of `k` of its elements, in MATLAB's order.

Combinations of a char or cell vector are not supported.

## Example

```matlab
nchoosek(5, 2)
nchoosek([1 2 3 4], 3)
```

## See also


