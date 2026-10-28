# contains

True where text contains a pattern.

## Syntax

    tf = contains(str, pattern)
    tf = contains(str, pattern, 'IgnoreCase', true)

## Description

`contains(str, pattern)` is true if `str` contains `pattern` anywhere. `pattern` may be a cell array of several patterns, and then the answer is true if any of them is found. On a cell array of character vectors the result is a logical array of the cell's shape, one value per element.

`'IgnoreCase', true` ignores letter case. MATLAB's `pattern` objects are not supported; for wildcards and classes of characters use [regexp](regexp).

## Example

```matlab
files = {'run1.csv', 'notes.txt', 'run2.CSV'};
isCsv = contains(files, '.csv', 'IgnoreCase', true)
```

## See also

[startsWith](startsWith) · [endsWith](endsWith) · [strfind](strfind) · [regexp](regexp)
