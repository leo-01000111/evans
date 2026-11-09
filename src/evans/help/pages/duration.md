# duration

A length of time.

## Syntax

    d = duration(h, m, s)
    d = duration('hh:mm:ss')
    d = duration(..., 'Format', fmt)

## Description

Shown as `hh:mm:ss` unless `'Format'` says `'s'`, `'m'`, `'h'`, `'d'`, `'y'`, `'dd:hh:mm:ss'`, `'mm:ss'` or `'hh:mm'`. Add and subtract durations, multiply or divide by a number, divide two durations for a ratio, and compare them. A plain number added to a duration is a number of days.

## Example

```matlab
d = duration(1,30,0)
d * 2
d / duration(0,45,0)
```

## See also

[hours](hours) · [datetime](datetime)
