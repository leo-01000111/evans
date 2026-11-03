# ls

List the files in the current folder.

## Syntax

    ls
    ls pattern

## Description

`ls` prints the names in the current folder, or those matching `pattern` (`ls *.m`). It is [dir](dir) with only the names. Evans does not return its output; use `d = dir` and `{d.name}` instead.

## Example

```matlab
fclose(fopen('a.txt', 'w'));
ls
```

## See also

[dir](dir) · [exist](exist)
