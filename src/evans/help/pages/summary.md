# summary

Print a summary of each variable of a table.

## Syntax

    summary(T)

## Description

Prints the size and type of each variable, with minimum, median, maximum and the number of missing values for numbers.

## Example

```matlab
summary(table([1;2;4], 'VariableNames', {'x'}))
```

## See also

[table](table)
