# false

Logical 0, or an array of logical zeros.

## Syntax

    F = false
    F = false(n)
    F = false(m, n)
    F = false([m n])
    F = false(m, n, p, ...)
    F = false(..., 'like', p)

## Description

`false` is the scalar logical 0. `false(n)` is an n-by-n logical array of zeros, and `false(m, n)` or `false([m n])` gives m rows and n columns. Three or more sizes make an N-D array. `'like', p` is accepted; the result is logical either way.

The usual use is a mask that a loop then marks: start with `false(size(x))` and set the elements that pass a test.

## Example

```matlab
x = [3 -1 4 -1 5];
keep = false(size(x));
keep(x > 0) = true;
x(keep)
```

## See also

[true](true) · [logical](logical) · [zeros](zeros)
