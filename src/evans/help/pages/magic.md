# magic

A magic square.

## Syntax

    M = magic(n)

## Description

`M` is an `n`-by-`n` matrix of the integers 1 to `n^2` whose rows, columns and both diagonals add to the same number. The values are MATLAB's own for every `n`.

## Example

```matlab
magic(4)
sum(magic(5))
```

## See also

[zeros](zeros) · [ones](ones) · [eye](eye) · [reshape](reshape)
