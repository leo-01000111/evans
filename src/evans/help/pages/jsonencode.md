# jsonencode

Write a value as JSON text.

## Syntax

    text = jsonencode(value)
    text = jsonencode(value, 'PrettyPrint', true)

## Description

A struct becomes an object, a vector an array, a matrix an array of rows, a cell an array, char a string and a logical `true` or `false`. `NaN` and `Inf` become `null`. `'PrettyPrint', true` indents the text.

## Example

```matlab
s.name = 'motor';
s.gains = [1.2 0.5];
jsonencode(s)
```

## See also

[jsondecode](jsondecode)
