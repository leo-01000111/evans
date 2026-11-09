# uiputfile

Ask the user where to save a file.

## Syntax

    [file, path] = uiputfile(filter, title, defname)

## Description

As [uigetfile](uigetfile), for a name that need not exist yet. Cancel gives `0`. Headless (a script run without a window, or a test) the dialog is not shown and the call behaves as if the user pressed Cancel.

## Example

```matlab
[file, path] = uiputfile('*.mat', 'Save results', 'results.mat');
if ~isequal(file, 0)
    disp(fullfile(path, file))
end
```

## See also

[uigetfile](uigetfile) · [uigetdir](uigetdir)
