# array2timetable

A timetable from a matrix.

## Syntax

    TT = array2timetable(A, 'RowTimes', t)

## Description

Each column becomes a variable.

## Example

```matlab
TT = array2timetable([1 2; 3 4], 'RowTimes', hours([1;2]))
```

## See also

[timetable](timetable)
