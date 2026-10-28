# ismember

Which elements of one array occur in another.

## Syntax

    tf = ismember(A, S)
    [tf, loc] = ismember(A, S)
    [tf, loc] = ismember(A, S, 'rows')

## Description

`ismember(A, S)` returns a logical array the shape of `A`, true where the element of `A` occurs somewhere in `S`. `loc` holds, for each element, the lowest linear index in `S` where it occurs, or 0. `NaN` is never a member.

For text, `ismember('b', {'a', 'b'})` checks a character vector against a cell of them, and a cell of character vectors is checked element by element. Two character vectors compare character by character.

`'rows'` treats each row of `A` and `S` as one item; `tf` and `loc` are then columns. Evans supports no other options.

## Example

```matlab
[tf, loc] = ismember([1 5 2 9], [2 1 1 7])
ismember('motor', {'pump', 'motor'})
```

## See also

[isequal](isequal) · [find](find) · [sort](sort)
