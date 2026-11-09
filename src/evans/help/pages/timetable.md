# timetable

A table whose rows are labelled by time.

## Syntax

    TT = timetable(times, var1, ..., varN)
    TT = timetable(var1, ..., 'RowTimes', times)
    TT = timetable(var1, ..., 'TimeStep', dt)

## Description

`times` is a datetime or duration column. Rows are picked by number, by a logical mask, by a datetime that matches exactly, or by `timerange(t1, t2)`: `TT(timerange(a, b), :)`. `TT.Time` is the row times. `array2timetable`, `table2timetable` and `timetable2table` convert.

## Example

```matlab
t = datetime(2024,1,15) + days((0:3)');
TT = timetable(t, [1;2;3;4], 'VariableNames', {'x'});
TT(timerange(t(1), t(3)), :)
```

## See also

[timerange](timerange) · [table](table)
