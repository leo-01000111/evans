# lower

Convert text to lowercase.

## Syntax

    newStr = lower(str)

## Description

`lower(str)` converts every uppercase letter in `str` to lowercase. On a cell array of character vectors it converts each element and keeps the cell's shape. Anything other than text is an error.

## Example

```matlab
lower({'STEP'; 'Bode'})
```

## See also

[upper](upper) · [isstrprop](isstrprop)
