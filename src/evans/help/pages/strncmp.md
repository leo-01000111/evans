# strncmp

Compare the first n characters of text.

## Syntax

    tf = strncmp(s1, s2, n)

## Description

`strncmp(s1, s2, n)` is true if `s1` and `s2` are character vectors whose first `n` characters are the same, case included. A string shorter than `n` compares only as far as it goes, so it matches only an identical string. Anything that is not text compares false.

If either argument is a cell array, the result is a logical array of its shape, comparing element by element; a 1×1 cell or a character vector is compared with every element.

## Example

```matlab
strncmp({'step', 'stepinfo', 'bode'}, 'step', 4)
```

## See also

[strncmpi](strncmpi) · [startsWith](startsWith)
