# datevec

A date as a vector of its parts.

## Syntax

    v = datevec(n)
    v = datevec(text)
    v = datevec(text, format)

## Description

`datevec` splits a serial date number, or a date as text, into `[year month day hour minute seconds]`. Several dates give one row each.

## Example

```matlab
datevec(datenum(2026, 11, 3, 12, 30, 0))
```

## See also

[datenum](datenum) · [datestr](datestr) · [clock](clock)
