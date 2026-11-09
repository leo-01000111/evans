# uigetfile

Ask the user to pick a file to open.

## Syntax

    [file, path] = uigetfile
    [file, path, idx] = uigetfile(filter, title, defname)
    [...] = uigetfile(..., 'MultiSelect', 'on')

## Description

`filter` is `'*.m'`, `'*.m;*.mlx'` or a cell array of patterns and descriptions, `{'*.csv', 'Data'; '*.*', 'All'}`. `path` ends with a separator. With `'MultiSelect', 'on'` `file` is a cell array of names. On Cancel all three outputs are `0`. Headless (a script run without a window, or a test) the dialog is not shown and the call behaves as if the user pressed Cancel.

## Example

```matlab
[file, path] = uigetfile('*.m', 'Pick a script');
if isequal(file, 0)
    disp('cancelled')
else
    disp(fullfile(path, file))
end
```

## See also

[uiputfile](uiputfile) · [uigetdir](uigetdir)
