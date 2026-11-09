# splitapply

Apply a function to each group of data.

## Syntax

    y = splitapply(fun, X, G)

## Description

`G` comes from `findgroups`; `fun` must return one value per group.

## Example

```matlab
x = [1;2;3;4];
g = findgroups([1;2;1;2]);
splitapply(@sum, x, g)
```

## See also

[findgroups](findgroups)
