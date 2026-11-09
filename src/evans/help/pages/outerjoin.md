# outerjoin

Join two tables, keeping unmatched rows.

## Syntax

    C = outerjoin(A, B, 'Keys', k)
    C = outerjoin(A, B, 'Type', type, 'MergeKeys', true)

## Description

`'Type'` is `'full'` (the default), `'left'`, `'right'`. Missing values are NaN or empty text. Without `'MergeKeys'` the key appears twice, as `k_left` and `k_right`.

## Example

```matlab
A = table([1;2],[5;6],'VariableNames',{'k','v'});
B = table([2;3],[8;9],'VariableNames',{'k','w'});
outerjoin(A, B, 'Keys', 'k', 'MergeKeys', true)
```

## See also

[innerjoin](innerjoin)
