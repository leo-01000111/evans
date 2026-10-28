# strjoin

Join the character vectors of a cell array into one.

## Syntax

    str = strjoin(C)
    str = strjoin(C, delimiter)

## Description

`strjoin(C)` joins the elements of the 1×N cell array `C` with a space between each. `strjoin(C, delimiter)` puts `delimiter` between them instead; escape sequences such as `'\n'` in it are read. If `delimiter` is a cell array of N−1 character vectors, they go between the elements in turn.

Every element of `C` must be a character vector; convert numbers first with [num2str](num2str) or [sprintf](sprintf).

## Example

```matlab
names = {'Kp', 'Ki', 'Kd'};
s = strjoin(names, ', ')
```

## See also

[strsplit](strsplit) · [join](join) · [sprintf](sprintf)
