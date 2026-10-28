# cellfun

Apply a function to each element of a cell array.

## Syntax

    A = cellfun(func, C)
    A = cellfun(func, C1, C2, ...)
    [A, B, ...] = cellfun(func, C, ...)
    A = cellfun(func, C, 'UniformOutput', false)
    A = cellfun('isempty', C)

## Description

`cellfun(func, C)` calls the function handle `func` on each element `C{k}` and collects the results in an array the same shape as `C`: a 2×3 cell gives a 2×3 array, a row a row, a column a column. Each result must be a scalar (a number, logical, single character or struct), and all of the same class; otherwise cellfun stops with MATLAB's error "Non-scalar in Uniform output" or "Mismatch in type of outputs".

With several cells of the same size, `func` gets one element from each. With several outputs, `func` is called asking for that many outputs, and each output is collected separately.

`'UniformOutput', false` collects the results in a cell of the same shape instead, so they can be anything.

The old string forms `'isempty'`, `'islogical'`, `'isreal'`, `'length'`, `'ndims'`, `'prodofsize'`, `cellfun('size', C, k)` and `cellfun('isclass', C, name)` work too; any other string names a function.

Evans does not support the `'ErrorHandler'` option; use `try`/`catch` inside the function. An anonymous function `@(x) ...` gives one output only, so for `[a, b] = cellfun(...)` pass a handle to the function itself, such as `@max`.

## Example

```matlab
c = {[1 5 2], [7 3], 4};
n = cellfun(@numel, c)
[m, k] = cellfun(@max, {[1 5 2], [7 3]})
d = cellfun(@(x) 2*x, c, 'UniformOutput', false)
```

## See also

[arrayfun](arrayfun) · [cell2mat](cell2mat) · [iscellstr](iscellstr) · [numel](numel)
