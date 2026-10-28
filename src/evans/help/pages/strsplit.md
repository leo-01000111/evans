# strsplit

Split a character vector at a delimiter into a cell array.

## Syntax

    C = strsplit(str)
    C = strsplit(str, delimiter)
    C = strsplit(..., 'CollapseDelimiters', false)
    C = strsplit(..., 'DelimiterType', 'RegularExpression')
    [C, matches] = strsplit(...)

## Description

`strsplit(str)` splits `str` at whitespace and returns the pieces as a 1×N cell array of character vectors. `strsplit(str, delimiter)` splits at `delimiter` instead; `delimiter` may be a cell array of several delimiters, and escape sequences such as `'\t'` and `'\n'` in it stand for tab and newline.

Consecutive delimiters count as one unless you pass `'CollapseDelimiters', false`, which gives an empty piece between each pair. A delimiter at the very start or end still leaves an empty piece there. With `'DelimiterType', 'RegularExpression'` the delimiters are [regexp](regexp) patterns. The second output is a cell of the delimiters that were found.

`str` must be a single character vector; split a cell of them with [split](split) or [regexp](regexp).

## Example

```matlab
parts = strsplit('a,b,,c', ',')
words = strsplit('one  two three')
```

## See also

[strjoin](strjoin) · [split](split) · [regexp](regexp) · [strtrim](strtrim)
