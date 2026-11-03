# bartlett

Bartlett (triangular, zero-ended) window.

## Syntax

    w = bartlett(L)

## Description

A column of `L` samples of a triangle that is zero at both ends. [triang](triang) is the one that is not.

## Example

```matlab
bartlett(5)'
```

## See also

[triang](triang) · [window](window)
