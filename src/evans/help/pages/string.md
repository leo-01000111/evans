# string

Convert to a string array.

## Syntax

    S = string(A)

## Description

A string (`"abc"`) is one element holding text, unlike a character vector (`'abc'`) with one element per character. `string(A)` turns a character vector into a string, a cell array of text into a string array, and numbers into their text. `class` says `string`, `numel("abc")` is 1, `+` joins strings and `==` compares them.

## Example

```matlab
s = string('hello')
t = ["a" "bc"]
numel(t)
s + " world"
```

## See also

[strlength](strlength) · [isstring](isstring) · [join](join)
