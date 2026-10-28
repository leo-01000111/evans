# isspace

True for whitespace characters.

## Syntax

    tf = isspace(str)

## Description

`isspace(str)` returns a logical array the size of `str`, true where the character is a space, tab, newline or other whitespace. For anything that is not text the result is all false.

## Example

```matlab
isspace(sprintf('a b\tc'))
```

## See also

[isletter](isletter) · [isstrprop](isstrprop) · [strtrim](strtrim)
