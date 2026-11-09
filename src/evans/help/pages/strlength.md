# strlength

Number of characters in each string.

## Syntax

    n = strlength(S)

## Description

For a string or character vector, the number of characters. For a string array, a number for each element. `numel` counts elements; `strlength` counts characters.

## Example

```matlab
strlength("hello")
numel("hello")
strlength(["a" "bcd"])
```

## See also

[numel](numel) · [string](string) · [length](length)
