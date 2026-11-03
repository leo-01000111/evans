# xlswrite

Write a matrix or a cell array to an Excel workbook.

## Syntax

    xlswrite(filename, A)
    xlswrite(filename, A, sheet)
    xlswrite(filename, A, sheet, range)
    xlswrite(filename, A, range)

## Description

`xlswrite` writes `A` to a `.xlsx` workbook, from cell A1 or from the top-left cell of `range`. `A` is a numeric matrix, or a cell array of numbers and text. NaN and empty cells are left blank.

An existing workbook is updated in place: the cells written are replaced and every other cell and sheet is kept. A sheet that does not exist yet is added. MATLAB now recommends [writematrix](writematrix) and [writetable](writetable), which write workbooks too.

## Example

```matlab
xlswrite('out.xlsx', [16 2 3; 5 11 10]);
xlswrite('out.xlsx', {'note'}, 'Sheet1', 'E1');
[num, txt] = xlsread('out.xlsx')
```

## See also

[xlsread](xlsread) · [writematrix](writematrix) · [writetable](writetable) · [sheetnames](sheetnames)
