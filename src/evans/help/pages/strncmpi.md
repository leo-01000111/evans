# strncmpi

Compare the first n characters of text, ignoring case.

## Syntax

    tf = strncmpi(s1, s2, n)

## Description

`strncmpi(s1, s2, n)` is [strncmp](strncmp) with letter case ignored: true if the first `n` characters of `s1` and `s2` match apart from case. Cell arrays are compared element by element, giving a logical array of the cell's shape.

## Example

```matlab
strncmpi('STEP', 'stepinfo', 4)
```

## See also

[strncmp](strncmp) · [startsWith](startsWith)
