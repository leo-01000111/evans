# split

Split text at delimiters into a column cell array.

## Syntax

    C = split(str)
    C = split(str, delimiter)
    C = split(..., 'CollapseDelimiters', false)
    [C, matches] = split(...)

## Description

`split(str)` splits `str` at whitespace, treating a run of whitespace as one delimiter. `split(str, delimiter)` splits at `delimiter`, which may be a cell array of several delimiters. Pass `'CollapseDelimiters', false` to keep an empty piece between consecutive delimiters.

MATLAB returns a string array; Evans has no string arrays yet, so `split` returns an N×1 cell array of character vectors with the same pieces. For an M×1 cell of text, each string becomes one row of an M×N cell, and every string must split into the same number of pieces. Evans does not split a row cell or a matrix of text.

## Example

```matlab
C = split('x y  z')
```

## See also

[join](join) · [strsplit](strsplit) · [regexp](regexp)
