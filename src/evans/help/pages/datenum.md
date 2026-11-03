# datenum

A date as a serial date number.

## Syntax

    n = datenum(y, m, d)
    n = datenum(y, m, d, h, mi, s)
    n = datenum(v)
    n = datenum(text)
    n = datenum(text, format)

## Description

A serial date number counts days from the start of year 0, so `datenum(2000, 1, 1)` is 730486 and adding 1 is the next day. The date can be numbers (which may overflow: month 13 is next January), a date vector with 3 or 6 columns, or text in a common form such as `'2026-11-03'` or `'03-Nov-2026 14:30:00'`, with `format` when it is ambiguous. A cell of texts gives a column.

## Example

```matlab
datenum(2026, 11, 3)
datenum('2026-11-03') - datenum('2026-01-01')
```

## See also

[datevec](datevec) · [datestr](datestr) · [now](now)
