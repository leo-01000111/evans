# cell2struct

Build a struct from a cell array of values and a list of field names.

## Syntax

    s = cell2struct(C, fields)
    s = cell2struct(C, fields, dim)

## Description

`cell2struct(C, fields, dim)` takes the field names from `fields` (a name or a cell of names) and their values from `C`. Along dimension `dim` (1 by default) there must be one entry per field; each slice along the other dimension becomes one struct, and several make a column struct array.

`cell2struct({'Bob'; 30}, {'name'; 'age'}, 1)` and `cell2struct({'Bob', 30}, {'name', 'age'}, 2)` both make one struct. A 2×3 cell with two fields and `dim = 1` makes a 3×1 struct array, one struct per column.

Evans supports `dim` 1 and 2 only (2-D arrays).

## Example

```matlab
s = cell2struct({'Bob'; 30}, {'name'; 'age'}, 1)
t = cell2struct({1, 2; 'x', 'y'}, {'n'; 'tag'}, 1);
t(2).tag
```

## See also

[struct2cell](struct2cell) · [rmfield](rmfield) · [isfield](isfield)
