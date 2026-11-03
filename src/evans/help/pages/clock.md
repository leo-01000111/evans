# clock

The current date and time as a vector.

## Syntax

    c = clock

## Description

A row `[year month day hour minute seconds]`, with fractional seconds. MATLAB now recommends `datetime`, which Evans does not have yet.

## Example

```matlab
c = clock;
c(1)
```

## See also

[now](now) · [datestr](datestr) · [datevec](datevec)
