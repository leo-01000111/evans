# warndlg

Show a warning message box.

## Syntax

    warndlg(message, title)
    h = warndlg(...)

## Description

`message` is a string, or a cell array of lines. The call waits until the box is closed, which MATLAB's does not. `h` is a placeholder handle. Headless the box is not shown and the call does nothing.

## Example

```matlab
warndlg('Run finished', 'Done')
```

## See also

[msgbox](msgbox) · [errordlg](errordlg) · [warndlg](warndlg) · [questdlg](questdlg)
