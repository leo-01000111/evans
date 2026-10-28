# arrayfun

Apply a function to each element of an array.

## Syntax

    A = arrayfun(func, X)
    A = arrayfun(func, X1, X2, ...)
    [A, B, ...] = arrayfun(func, X, ...)
    A = arrayfun(func, X, 'UniformOutput', false)

## Description

`arrayfun(func, X)` calls the function handle `func` on each element of `X` and returns the results in an array the same shape as `X`. `X` can be numeric, logical, char (each element is one character), a struct array (each element is one struct) or a cell (each element arrives as a 1×1 cell).

Each result must be a scalar of the same class as the others; structs make a struct array. With several arrays of the same size, `func` gets one element from each; with several outputs, each is collected separately.

`'UniformOutput', false` returns a cell of the results instead, so they can be any size.

Evans does not support the `'ErrorHandler'` option, or arrayfun over systems and symbolic arrays.

## Example

```matlab
s = struct('name', {'a', 'b'}, 'gain', {2, 5});
g = arrayfun(@(e) e.gain, s)
sq = arrayfun(@(x) x^2, [1 2; 3 4])
r = arrayfun(@(n) 1:n, 1:3, 'UniformOutput', false)
```

## See also

[cellfun](cellfun) · [deal](deal) · [repmat](repmat)
