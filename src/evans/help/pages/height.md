# height

The number of rows of a table, or of an array.

## Syntax

    n = height(T)

## Description

`height(T)` is the number of rows, `size(T, 1)`. It works on matrices and cell arrays as well as tables.

## Example

```matlab
T = table([1; 2; 3], [4; 5; 6]);
height(T)
width(T)
```

## See also

[width](width) · [size](size) · [table](table)
