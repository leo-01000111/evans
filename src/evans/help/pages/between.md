# between

The calendar steps from one datetime to another.

## Syntax

    c = between(t1, t2)

## Description

Months, then days, then time of day, so `t1 + between(t1, t2)` is `t2`.

## Example

```matlab
between(datetime(2024,1,15), datetime(2024,3,1,10,30,0))
```

## See also

[datetime](datetime) · [dateshift](dateshift)
