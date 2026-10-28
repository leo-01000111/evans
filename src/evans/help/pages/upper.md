# upper

Convert text to uppercase.

## Syntax

    newStr = upper(str)

## Description

`upper(str)` converts every lowercase letter in `str` to uppercase. On a cell array of character vectors it converts each element and keeps the cell's shape. Anything other than text is an error.

## Example

```matlab
upper('pid tuning')
```

## See also

[lower](lower) · [isstrprop](isstrprop)
