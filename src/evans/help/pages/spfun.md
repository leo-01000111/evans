# spfun

Apply a function to the nonzeros only.

## Syntax

    F = spfun(fun, S)

## Description

`fun` sees just the stored values, so `spfun(@exp, S)` leaves the zeros at zero, unlike `exp(S)`.

## Example

```matlab
S = sparse([1 2], [1 2], [0 1]);
full(spfun(@exp, S))
```

## See also

[sparse](sparse) · [spones](spones)
