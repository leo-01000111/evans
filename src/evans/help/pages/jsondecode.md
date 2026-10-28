# jsondecode

Read JSON text into structs, arrays and cells.

## Syntax

    value = jsondecode(text)

## Description

A JSON object becomes a struct, an array of numbers a column vector, an array of arrays of the same length a matrix, an array of objects with the same fields a struct array, and any other array a column cell. `true` and `false` become logical values, and `null` becomes `[]`.

## Example

```matlab
s = jsondecode('{"name": "motor", "gains": [1.2, 0.5, 0.01]}');
s.name
s.gains
```

## See also

[jsonencode](jsonencode)
