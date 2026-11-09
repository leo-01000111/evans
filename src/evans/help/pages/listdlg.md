# listdlg

Dialog to choose from a list.

## Syntax

    [indx, tf] = listdlg('ListString', items)
    [indx, tf] = listdlg('ListString', items, 'SelectionMode', 'single', 'Name', name, 'PromptString', text, 'InitialValue', k)

## Description

`indx` holds the positions chosen (1-based); `tf` is 1 for OK and 0 for Cancel. Headless (a script run without a window, or a test) the dialog is not shown and the call behaves as if the user pressed Cancel.

## Example

```matlab
[k, ok] = listdlg('ListString', {'step', 'bode', 'nyquist'}, 'SelectionMode', 'single');
ok
```

## See also

[questdlg](questdlg) · [inputdlg](inputdlg)
