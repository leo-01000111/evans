# strtrim

Remove leading and trailing whitespace.

## Syntax

    newStr = strtrim(str)

## Description

`strtrim(str)` removes spaces, tabs, newlines and other whitespace (and null characters) from both ends of `str`. On a cell array of character vectors it trims each one and keeps the cell's shape.

Like MATLAB's, it keeps the "significant" whitespace characters such as the nonbreaking space `char(160)`. Anything other than text is an error.

## Example

```matlab
s = strtrim(sprintf('  value \n'))
c = strtrim({' a', 'b  '})
```

## See also

[deblank](deblank) · [strrep](strrep) · [strsplit](strsplit)
