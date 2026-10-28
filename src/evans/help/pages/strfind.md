# strfind

Starting positions of a pattern in text.

## Syntax

    k = strfind(str, pattern)
    k = strfind(..., 'ForceCellOutput', true)

## Description

`strfind(str, pattern)` returns a row vector of the positions, counting from 1, where `pattern` begins in `str`. Overlapping occurrences all count: `strfind('aaa', 'aa')` is `[1 2]`. When `pattern` is not found, or is empty, the result is empty.

On a cell array of character vectors the result is a cell of the same shape holding one row of positions per element. `'ForceCellOutput', true` returns a cell even for a single character vector.

## Example

```matlab
k = strfind('step response step', 'step')
```

## See also

[contains](contains) · [regexp](regexp) · [strrep](strrep) · [find](find)
