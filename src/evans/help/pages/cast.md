# cast

Convert to a class by name.

## Syntax

    B = cast(A, newclass)

## Description

`cast(A, 'int8')` is `int8(A)`, and likewise for the other numeric classes, `'single'`, `'double'` and `'logical'`.

## Example

```matlab
cast(300, 'uint8')
cast([1.7 2.2], 'int16')
```

## See also

[double](double) · [single](single) · [int8](int8) · [logical](logical)
