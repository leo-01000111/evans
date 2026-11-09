# logical

Convert to logical.

## Syntax

    B = logical(A)

## Description

`logical(A)` is 1 (true) wherever `A` is not zero and 0 elsewhere. `NaN` cannot be converted and is an error.

## Example

```matlab
logical([1 0 2 -3])
class(ans)
```

## See also

[double](double) · [cast](cast)
