# datetime

A point in time.

## Syntax

    t = datetime(y, m, d)
    t = datetime(y, m, d, h, mi, s)
    t = datetime('2024-01-15')
    t = datetime(text, 'InputFormat', fmt)
    t = datetime(x, 'ConvertFrom', 'datenum')
    t = datetime('now')

## Description

Arguments broadcast, and a month or day past its range rolls over (`datetime(2024,13,1)` is January 2025). Text is read in the common ISO and `dd-MMM-yyyy` forms, or by `'InputFormat'`. `'ConvertFrom'` takes `'datenum'`, `'posixtime'`, `'excel'` or `'juliandate'`. `'Format'` sets how it is shown. `t.Year`, `t.Month`, `t.Day`, `t.Hour`, `t.Minute`, `t.Second` and `t.Format` read its parts.

Arithmetic: `t + duration` and `t - t2` (a duration), `t + number` adds days, `t + calmonths(1)` follows the calendar. Compare with `<`, `==`, and use `sort`, `min`, `max`, `diff`. Time zones are not supported. A scalar shows on one line (`t = 15-Jan-2024`), not under a `datetime` heading.

## Example

```matlab
t = datetime(2024,1,15,10,30,0);
t + hours(36)
t2 = datetime('2024-03-01');
t2 - t
t < t2
```

## See also

[duration](duration) · [between](between) · [dateshift](dateshift)
