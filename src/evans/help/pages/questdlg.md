# questdlg

Dialog with a question and buttons.

## Syntax

    answer = questdlg(question)
    answer = questdlg(question, title, btn1, btn2, defbtn)
    answer = questdlg(question, title, btn1, btn2, btn3, defbtn)

## Description

Returns the label of the button pressed, or `''` if the window was closed. With no buttons given they are Yes, No and Cancel. Headless (a script run without a window, or a test) the dialog is not shown and the call behaves as if the user pressed Cancel.

## Example

```matlab
choice = questdlg('Overwrite the file?', 'Save', 'Yes', 'No', 'No');
switch choice
    case 'Yes'
        disp('overwriting')
    otherwise
        disp('kept')
end
```

## See also

[inputdlg](inputdlg) · [msgbox](msgbox) · [listdlg](listdlg)
