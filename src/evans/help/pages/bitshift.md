# bitshift

Shift bits left or right.

## Syntax

    C = bitshift(A, n)

## Description

Shifts the bits of `A` left by `n` places, or right when `n` is negative. Bits shifted out of an integer class are lost.

## Example

```matlab
bitshift(1, 4)
bitshift(uint8(255), 1)
bitshift(16, -2)
```

## See also

[bitand](bitand) · [bitor](bitor) · [bitxor](bitxor)
