# iscellstr

True for a cell array whose elements are all character vectors.

## Syntax

    tf = iscellstr(C)

## Description

`iscellstr(C)` is true when `C` is a cell array and every element is a character vector. An empty cell `{}` counts; anything that is not a cell is false.

## Example

```matlab
iscellstr({'a', 'bc'})
iscellstr({'a', 1})
```

## See also

[cellfun](cellfun) · [ismember](ismember) · [cell2mat](cell2mat)
