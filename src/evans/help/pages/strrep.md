# strrep

Find and replace text.

## Syntax

    newStr = strrep(str, old, new)

## Description

`strrep(str, old, new)` replaces every occurrence of `old` in `str` with `new`. Overlapping occurrences are each replaced, as in MATLAB: `strrep('222', '22', '*')` is `'**'`. On a cell array of character vectors it works on each element and keeps the cell's shape.

Evans supports `old` and `new` as character vectors only, not cell arrays of them. For pattern-based replacement use [regexprep](regexprep).

## Example

```matlab
s = strrep('Kp = 1.0', '1.0', '2.5')
```

## See also

[regexprep](regexprep) · [strfind](strfind) · [strtrim](strtrim)
