# istable

Whether a value is a table.

## Syntax

    tf = istable(x)

## Description

True for a table made by [table](table), [readtable](readtable) or [array2table](array2table), false for anything else.

## Example

```matlab
istable(table([1; 2]))
istable([1 2])
```

## See also

[table](table) · [readtable](readtable)
