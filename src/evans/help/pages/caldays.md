# caldays

A calendar step of whole days.

## Syntax

    c = caldays(n)

## Description

Added to a datetime it moves by calendar days. `calweeks`, `calmonths`, `calquarters` and `calyears` are the others. Adding a month to 31 January gives the last day of February.

## Example

```matlab
datetime(2024,1,31) + calmonths(1)
datetime(2024,1,15) + caldays(20)
```

## See also

[calmonths](calmonths) · [between](between)
