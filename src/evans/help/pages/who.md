# who

List the variables in the workspace.

## Syntax

    who
    who pattern
    names = who(...)

## Description

`who` prints the names of the workspace's variables in alphabetical order; a pattern such as `who a*` lists only those that match. With an output it returns them as a column cell. The console's preset names, such as `s`, are not listed.

Inside a function, Evans's `who` still lists the workspace, not the function's own variables.

## Example

```matlab
a = 1; b = [1 2 3];
who
```

## See also

[whos](whos) · [clear](clear) · [exist](exist)
