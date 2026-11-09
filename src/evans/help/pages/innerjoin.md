# innerjoin

Join two tables on key variables, keeping matched rows.

## Syntax

    C = innerjoin(A, B)
    C = innerjoin(A, B, 'Keys', keys)
    [C, ia, ib] = innerjoin(A, B, 'LeftKeys', k1, 'RightKeys', k2)

## Description

The default keys are the variable names the tables share. The result is sorted by key. Other variables that share a name get `_left` and `_right`. `join` is the same when every row of `A` has a match in `B` and keeps `A`'s order.

## Example

```matlab
A = table([1;2;1],[5;6;7],'VariableNames',{'k','v'});
B = table([1;2],{'p';'q'},'VariableNames',{'k','w'});
innerjoin(A, B)
```

## See also

[outerjoin](outerjoin) · [join](join)
