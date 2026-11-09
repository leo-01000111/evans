# msgbox

Show a message box.

## Syntax

    msgbox(message)
    msgbox(message, title, icon)
    h = msgbox(...)

## Description

`message` is a string, or a cell array of lines. The call waits until the box is closed, which MATLAB's does not. `icon` is `'none'`, `'help'`, `'warn'` or `'error'`. `h` is a placeholder handle. Headless the box is not shown and the call does nothing.

## Example

```matlab
msgbox('Run finished', 'Done')
```

## See also

[msgbox](msgbox) · [errordlg](errordlg) · [warndlg](warndlg) · [questdlg](questdlg)
