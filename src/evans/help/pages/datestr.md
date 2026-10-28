# datestr

Convert a date to text.

## Syntax

    str = datestr(t)
    str = datestr(t, format)

## Description

`t` is a date number (as from `now` or `datenum`) or a date vector `[y m d h mi s]`. The default format is `'dd-mmm-yyyy HH:MM:SS'`. `format` is either a number from 0 to 31 (MATLAB's standard formats) or a pattern of MATLAB's symbols: `yyyy`, `yy`, `mmmm`, `mmm`, `mm` (month), `dd`, `ddd`, `HH`, `MM` (minutes), `SS`, `FFF` and `PM`.

`datetime` arrays are not in Evans yet.

## Example

```matlab
datestr(datenum(2026, 10, 28, 14, 5, 0))
datestr([2026 10 28 0 0 0], 'yyyy-mm-dd')
```

## See also


