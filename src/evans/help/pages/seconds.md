# seconds

A duration in seconds, or a duration as a number of seconds.

## Syntax

    d = seconds(x)
    x = seconds(d)

## Description

`seconds(5)` is a duration shown as `5 sec`; `seconds(d)` is the number of seconds in a duration `d`. `minutes`, `hours`, `days`, `years` and `milliseconds` work the same way.

## Example

```matlab
d = seconds([30 90])
seconds(minutes(2))
```

## See also

[duration](duration) · [hours](hours)
