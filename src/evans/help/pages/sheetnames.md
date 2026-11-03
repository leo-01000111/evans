# sheetnames

The names of the sheets in an Excel workbook.

## Syntax

    names = sheetnames(filename)

## Description

`sheetnames` returns a column cell of the sheet names of a `.xlsx` workbook, in the order they appear. Pass one of them, or its position, as the `'Sheet'` option of [readmatrix](readmatrix) or [readtable](readtable).

## Example

```matlab
writematrix([1 2], 'w.xlsx');
writematrix([3 4], 'w.xlsx', 'Sheet', 'Second');
names = sheetnames('w.xlsx')
```

## See also

[readmatrix](readmatrix) · [xlsread](xlsread)
