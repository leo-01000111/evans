# eigs

A few eigenvalues and eigenvectors of a large matrix.

## Syntax

    d = eigs(A)
    d = eigs(A, k)
    d = eigs(A, k, sigma)
    [V, D] = eigs(A, k, sigma)

## Description

The `k` (default 6) eigenvalues nearest the target `sigma`: `'largestabs'` (the default), `'smallestabs'`, `'largestreal'`, `'smallestreal'`, `'la'`, `'sa'`, or a number, for those closest to it. Sorted with the target's nearest first. A symmetric matrix uses the symmetric solver; small ones are solved densely. `eigs(A, B, ...)` solves the generalised problem for a small `B`. A function handle for `A`, and the options structure, are not supported.

## Example

```matlab
n = 60; e = ones(n, 1);
K = spdiags([-e 2*e -e], -1:1, n, n);
d = eigs(K, 3)
small = eigs(K, 2, 'smallestabs')
```

## See also

[eig](eig) · [svds](svds) · [sparse](sparse)
