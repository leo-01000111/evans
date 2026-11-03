# width

The number of variables of a table, or columns of an array.

## Syntax

    n = width(T)

## Description

`width(T)` is the number of table variables, `size(T, 2)`. It works on matrices and cell arrays as well as tables.

## Example

```matlab
width(table([1; 2], [3; 4], [5; 6]))
width(zeros(2, 7))
```

## See also

[height](height) · [size](size) · [table](table)
