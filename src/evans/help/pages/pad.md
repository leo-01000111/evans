# pad

Pad text with spaces or another character to a common length.

## Syntax

    newStr = pad(str)
    newStr = pad(str, n)
    newStr = pad(str, side)
    newStr = pad(str, n, side)
    newStr = pad(..., padCharacter)

## Description

`pad(C)` pads each character vector in the cell `C` with trailing spaces to the length of the longest. `pad(str, n)` pads to `n` characters; text that is already longer is left as it is, never cut. `side` is `'right'` (the default), `'left'` or `'both'`; with `'both'` an odd extra character goes on the right. `padCharacter` is a single character to pad with instead of a space.

MATLAB's `pad` also takes string arrays; Evans works on character vectors and cells of them.

## Example

```matlab
pad({'a', 'abc', 'ab'})
pad('7', 3, 'left', '0')
```

## See also

[blanks](blanks) · [strtrim](strtrim) · [strjoin](strjoin)
