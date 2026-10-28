# startsWith

True where text starts with a pattern.

## Syntax

    tf = startsWith(str, pattern)
    tf = startsWith(str, pattern, 'IgnoreCase', true)

## Description

`startsWith(str, pattern)` is true if `str` begins with `pattern`. `pattern` may be a cell array of several patterns (true if any matches). On a cell array of character vectors the result is a logical array of the cell's shape. `'IgnoreCase', true` ignores letter case.

## Example

```matlab
startsWith({'G_plant', 'K_ctrl', 'G_sensor'}, 'G_')
```

## See also

[endsWith](endsWith) · [contains](contains) · [strncmp](strncmp)
