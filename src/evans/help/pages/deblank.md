# deblank

Remove trailing whitespace and null characters.

## Syntax

    newStr = deblank(str)

## Description

`deblank(str)` removes whitespace and null characters (`char(0)`) from the end of `str`; leading whitespace stays. On a cell array of character vectors it works on each element and keeps the cell's shape.

## Example

```matlab
s = deblank(['name   ' char(0)])
```

## See also

[strtrim](strtrim) · [blanks](blanks)
