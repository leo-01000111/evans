# true

Logical 1, or an array of logical ones.

## Syntax

    T = true
    T = true(n)
    T = true(m, n)
    T = true([m n])
    T = true(m, n, p, ...)
    T = true(..., 'like', p)

## Description

`true` is the scalar logical 1. `true(n)` is an n-by-n logical array of ones, and `true(m, n)` or `true([m n])` gives m rows and n columns. Three or more sizes make an N-D array. `'like', p` is accepted; the result is logical either way.

A variable named `true` hides the function, as in MATLAB; `clear true` brings it back.

## Example

```matlab
mask = true(1, 5);
mask(3) = false
class(mask)
```

## See also

[false](false) · [logical](logical) · [ones](ones)
