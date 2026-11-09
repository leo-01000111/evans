# inputdlg

Dialog with text fields.

## Syntax

    answer = inputdlg(prompt)
    answer = inputdlg(prompt, title, dims, definput)

## Description

`prompt` is a string or a cell array of strings, one field each. `answer` is a column cell array of what was typed, or an empty cell if the user cancelled. `dims` gives the height of each field in lines. `definput` is a cell array of starting texts. Headless (a script run without a window, or a test) the dialog is not shown and the call behaves as if the user pressed Cancel.

## Example

```matlab
answer = inputdlg({'Gain', 'Delay'}, 'Parameters', 1, {'2', '0.1'});
if ~isempty(answer)
    K = str2double(answer{1})
end
```

## See also

[questdlg](questdlg) · [listdlg](listdlg) · [input](input)
