# dateshift

Move a datetime to the start or end of a unit.

## Syntax

    s = dateshift(t, 'start', unit)
    s = dateshift(t, 'end', unit)

## Description

`unit` is `'year'`, `'quarter'`, `'month'`, `'week'`, `'day'`, `'hour'`, `'minute'` or `'second'`.

## Example

```matlab
dateshift(datetime(2024,5,17,13,0,0), 'start', 'month')
```

## See also

[datetime](datetime)
