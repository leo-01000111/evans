# timerange

A row subscript that selects a span of time.

## Syntax

    r = timerange(t1, t2)
    r = timerange(t1, t2, interval)

## Description

`interval` is `'openright'` (the default: from `t1` up to but not including `t2`), `'closed'`, `'open'` or `'openleft'`.

## Example

```matlab
t = datetime(2024,1,1) + days((0:4)');
TT = timetable(t, (1:5)');
TT(timerange(t(2), t(4), 'closed'), :)
```

## See also

[timetable](timetable)
