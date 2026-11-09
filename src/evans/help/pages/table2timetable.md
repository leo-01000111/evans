# table2timetable

A timetable from a table with a datetime or duration variable.

## Syntax

    TT = table2timetable(T)

## Description

The first such variable becomes the row times.

## Example

```matlab
T = table(datetime(2024,1,1) + days([0;1]), [5;6], 'VariableNames', {'t','v'});
table2timetable(T)
```

## See also

[timetable](timetable)
