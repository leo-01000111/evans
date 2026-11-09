# calmonths

A calendar step of months.

## Syntax

    c = calmonths(n)

## Description

See `caldays`. The day of the month is kept, or clipped to the month's last day.

## Example

```matlab
datetime(2024,1,31) + calmonths(1)
```

## See also

[caldays](caldays)
