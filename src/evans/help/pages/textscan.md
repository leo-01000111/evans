# textscan

Read columns of formatted data from a file or text.

## Syntax

    C = textscan(fid, format)
    C = textscan(text, format)
    C = textscan(..., Name, Value)

## Description

`textscan` reads the data as columns, one conversion each, and returns a 1×N cell: `%f` and `%d` give a numeric column, `%s` a column cell of char. `'Delimiter'` sets the field separator and `'HeaderLines'` skips lines first. An empty numeric field is `NaN`.

Conversions other than `%f`, `%d`, `%u`, `%s`, `%q`, `%c` and skipped fields (`%*f`) are not supported.

## Example

```matlab
C = textscan('a 1.5\nb 2.5', '%s %f');
names = C{1}
values = C{2}
```

## See also

[readtable](readtable) · [fgetl](fgetl) · [strsplit](strsplit)
