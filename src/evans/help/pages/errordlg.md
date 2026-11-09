# errordlg

Show a error message box.

## Syntax

    errordlg(message, title)
    h = errordlg(...)

## Description

`message` is a string, or a cell array of lines. The call waits until the box is closed, which MATLAB's does not. `h` is a placeholder handle. Headless the box is not shown and the call does nothing.

## Example

```matlab
errordlg('Run finished', 'Done')
```

## See also

[msgbox](msgbox) · [errordlg](errordlg) · [warndlg](warndlg) · [questdlg](questdlg)
