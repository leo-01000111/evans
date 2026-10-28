# endsWith

True where text ends with a pattern.

## Syntax

    tf = endsWith(str, pattern)
    tf = endsWith(str, pattern, 'IgnoreCase', true)

## Description

`endsWith(str, pattern)` is true if `str` ends with `pattern`. `pattern` may be a cell array of several patterns (true if any matches). On a cell array of character vectors the result is a logical array of the cell's shape. `'IgnoreCase', true` ignores letter case.

## Example

```matlab
endsWith({'data.csv', 'plot.png'}, {'.csv', '.txt'})
```

## See also

[startsWith](startsWith) · [contains](contains)
