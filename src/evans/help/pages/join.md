# join

Join the text in a cell array, with spaces or a delimiter.

## Syntax

    str = join(C)
    str = join(C, delimiter)
    str = join(C, delimiter, dim)

## Description

`join(C)` joins the character vectors of a 1×N cell array into one, with a space between each. `join(C, delimiter)` uses `delimiter` instead. For a cell with several rows, each row is joined and the result is a column cell; `dim` chooses whether to join along rows (2) or down columns (1).

MATLAB's `join` also takes string arrays and a cell of delimiters; Evans supports a cell of character vectors and a single character-vector delimiter.

## Example

```matlab
s = join({'a', 'b', 'c'}, '-')
```

## See also

[split](split) · [strjoin](strjoin)
