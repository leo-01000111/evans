# validateattributes

Check a value's class and properties.

## Syntax

    validateattributes(A, classes, attributes)
    validateattributes(A, classes, attributes, funcName, varName)

## Description

`classes` is a cell of class names (`'numeric'`, `'double'`, `'char'`, `'logical'`, `'cell'`, `'struct'`, `'function_handle'`). `attributes` is a cell of checks: `'scalar'`, `'vector'`, `'row'`, `'column'`, `'nonempty'`, `'square'`, `'positive'`, `'nonnegative'`, `'negative'`, `'nonzero'`, `'nonnan'`, `'finite'`, `'real'`, `'integer'`, `'binary'`, `'even'`, `'odd'`, `'increasing'`, `'decreasing'`, and the pairs `'>'`, `'>='`, `'<'`, `'<='`, `'numel'`, `'size'`, `'nrows'`, `'ncols'` followed by a number. A failed check raises an error naming the variable (`varName`, or `input`). Integer types do not exist in Evans yet, so `'single'` never matches.

## Example

```matlab
validateattributes(5, {'numeric'}, {'positive', 'scalar'})
validateattributes([1 2 3], {'numeric'}, {'vector', '>=', 1})
```

## See also

[isfield](isfield) · [cellfun](cellfun)
