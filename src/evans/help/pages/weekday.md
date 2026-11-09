# weekday

The day of the week of a datetime.

## Syntax

    n = weekday(t)
    [n, name] = weekday(t)

## Description

Sunday is 1. `name` is `'Mon'` and so on, or the full name with `weekday(t, 'long')`.

## Example

```matlab
[n, s] = weekday(datetime(2024,1,15))
```

## See also

[datetime](datetime)
