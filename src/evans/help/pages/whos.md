# whos

List the workspace's variables with their sizes and classes.

## Syntax

    whos
    whos pattern
    s = whos(...)

## Description

`whos` prints a table of name, size, bytes, class and attributes. Bytes are counted as MATLAB counts them for numbers (8 per double, 16 per complex double, 1 per logical, 2 per char); for cells and structs they are an estimate. With an output it returns a struct array with fields `name`, `size`, `bytes` and `class`.

## Example

```matlab
x = rand(3); name = 'motor';
whos
```

## See also

[who](who) · [size](size)
