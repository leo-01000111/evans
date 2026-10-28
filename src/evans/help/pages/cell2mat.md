# cell2mat

Join the contents of a cell array into one matrix.

## Syntax

    M = cell2mat(C)

## Description

`cell2mat(C)` places the arrays held in `C` as blocks: the blocks of each row of `C` side by side, then those rows one above the other. The blocks must fit, as in `[A, B; C, D]`.

All the elements must have the same class: numeric, logical or char. A cell holding cells, or mixing classes (such as `1` and `true`), is an error, as in MATLAB. Evans does not join cells of structs, and has no multi-row char arrays, so joining text must give one row.

## Example

```matlab
C = {[1 2], 3; [4 5], 6};
M = cell2mat(C)
```

## See also

[cellfun](cellfun) · [struct2cell](struct2cell) · [reshape](reshape) · [repmat](repmat)
