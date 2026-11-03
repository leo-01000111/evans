# xlsread

Read numbers and text from an Excel workbook.

## Syntax

    num = xlsread(filename)
    num = xlsread(filename, sheet)
    num = xlsread(filename, sheet, range)
    num = xlsread(filename, range)
    [num, txt, raw] = xlsread(...)

## Description

`xlsread` reads the first sheet of a `.xlsx` or `.xlsm` workbook, or the sheet named or numbered by `sheet`, limited to `range` (`'B2:D10'`) if given. A file name without an extension gets `.xlsx`.

`num` holds the numbers, with NaN for text and blanks, and loses the empty rows and columns around them, so a header row and a text column at the edge are cut away. `txt` is a cell of the text, `''` where numbers are, trimmed the same way. `raw` is a cell of everything: numbers as numbers, text as text, blanks as NaN.

Evans reads `.xlsx` through openpyxl, which cannot open the old `.xls` format or `.ods`; save those as `.xlsx`. Formulas read as the value Excel last saved. MATLAB now recommends [readmatrix](readmatrix) and [readtable](readtable), which read workbooks too.

## Example

```matlab
xlswrite('log.xlsx', {'t', 'y'; 0, 1.5; 1, 2.5});
[num, txt, raw] = xlsread('log.xlsx')
```

## See also

[xlswrite](xlswrite) · [readmatrix](readmatrix) · [readtable](readtable) · [sheetnames](sheetnames)
