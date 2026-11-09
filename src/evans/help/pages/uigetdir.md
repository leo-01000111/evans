# uigetdir

Ask the user to pick a folder.

## Syntax

    folder = uigetdir
    folder = uigetdir(start, title)

## Description

The folder path, or `0` on Cancel. Headless (a script run without a window, or a test) the dialog is not shown and the call behaves as if the user pressed Cancel.

## Example

```matlab
d = uigetdir(pwd, 'Pick a folder');
if ~isequal(d, 0)
    disp(d)
end
```

## See also

[uigetfile](uigetfile)
