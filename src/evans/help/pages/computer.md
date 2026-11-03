# computer

The kind of computer Evans is running on.

## Syntax

    c = computer
    [c, maxsize, endian] = computer
    arch = computer('arch')

## Description

`computer` is `'PCWIN64'`, `'MACA64'` (Apple Silicon), `'MACI64'` or `'GLNXA64'`; `computer('arch')` is the short form (`'win64'`, …). `maxsize` is the largest array size and `endian` is `'L'`.

## Example

```matlab
computer
ispc
```

## See also

[ispc](ispc) · [ismac](ismac) · [isunix](isunix)
