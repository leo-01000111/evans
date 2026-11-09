# sprand

Sparse matrix of uniform random numbers.

## Syntax

    R = sprand(m, n, density)
    R = sprand(S)

## Description

About `density*m*n` entries, uniform on (0, 1), at random positions. `sprand(S)` keeps the pattern of `S`. `rng(seed)` makes it repeatable (the numbers are not MATLAB's).

## Example

```matlab
rng(1);
R = sprand(6, 6, 0.25);
issparse(R)
```

## See also

[sparse](sparse) · [rand](rand) · [rng](rng)
