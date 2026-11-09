# timetable2table

A table from a timetable.

## Syntax

    T = timetable2table(TT)

## Description

The row times become the first variable.

## Example

```matlab
TT = timetable(hours([1;2]), [5;6]);
timetable2table(TT)
```

## See also

[timetable](timetable)
