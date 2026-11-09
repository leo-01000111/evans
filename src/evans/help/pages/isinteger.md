# isinteger

True for integer classes.

## Syntax

    tf = isinteger(A)

## Description

`isinteger(A)` is true when `A` is one of `int8` … `uint64`. A double that holds a whole number is not an integer in this sense.

## Example

```matlab
isinteger(int8(3))
isinteger(3)
```

## See also

[isfloat](isfloat) · [int8](int8)
