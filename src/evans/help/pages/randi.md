# randi

Random integers, uniformly distributed.

## Syntax

    X = randi(imax)
    X = randi(imax, n)
    X = randi(imax, m, n)
    X = randi(imax, [m n])
    X = randi([imin imax], ...)

## Description

`randi(imax)` returns one random integer between 1 and `imax`. `randi(imax, n)` returns an `n`-by-`n` matrix, `randi(imax, m, n)` an `m`-by-`n` one. `randi([imin imax], ...)` draws from `imin` to `imax` instead. The values are doubles.

[rng](rng) seeds the generator. Evans draws from numpy's Mersenne Twister, not MATLAB's stream, so the numbers differ from MATLAB's for the same seed. Evans does not support integer classes such as `'int8'`.

## Example

```matlab
rng(42);
rolls = randi(6, 1, 10)
```

## See also

[rand](rand) · [randperm](randperm) · [rng](rng)
