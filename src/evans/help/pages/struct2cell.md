# struct2cell

The values of a struct's fields, as a cell array.

## Syntax

    C = struct2cell(s)

## Description

`struct2cell(s)` returns an n×1 cell holding the values of the n fields of `s`, in the order of `fieldnames(s)`.

For an m×1 struct array the result is n×m, a column of values per element. For a 1×m struct array MATLAB returns an n×1×m array, and Evans, which has 2-D arrays only, refuses; convert one element at a time with `struct2cell(s(k))`.

## Example

```matlab
s.name = 'motor';
s.gain = 2.5;
c = struct2cell(s)
```

## See also

[cell2struct](cell2struct) · [rmfield](rmfield) · [orderfields](orderfields)
