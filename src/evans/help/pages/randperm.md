# randperm

Random permutation of the integers 1 to n.

## Syntax

    p = randperm(n)
    p = randperm(n, k)

## Description

`randperm(n)` returns a row vector with the integers 1 to `n` in random order. `randperm(n, k)` returns `k` of them, all different; `k` must not exceed `n`.

[rng](rng) seeds the generator. The permutation for a given seed differs from MATLAB's.

## Example

```matlab
rng(1);
randperm(8)
randperm(10, 3)
```

## See also

[randi](randi) · [rand](rand) · [rng](rng) · [sort](sort)
