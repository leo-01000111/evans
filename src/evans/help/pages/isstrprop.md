# isstrprop

True where characters belong to a category.

## Syntax

    tf = isstrprop(str, category)
    tf = isstrprop(..., 'ForceCellOutput', true)

## Description

`isstrprop(str, category)` returns a logical array the size of `str`, true where the character belongs to `category`: `'alpha'`, `'digit'`, `'alphanum'`, `'lower'`, `'upper'`, `'wspace'`, `'punct'`, `'cntrl'`, `'xdigit'`, `'graphic'`, `'print'` or `'ascii'`. On a cell array the result is a cell of logical arrays of the same shape. An unknown category is an error.

## Example

```matlab
isstrprop('Kp=2.5', 'digit')
```

## See also

[isletter](isletter) · [isspace](isspace) · [upper](upper)
