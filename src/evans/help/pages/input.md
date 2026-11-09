# input

Ask for a value at the console prompt.

## Syntax

    x = input(prompt)
    s = input(prompt, 's')

## Description

Shows `prompt` and waits for a line. The line is evaluated as an expression in the base workspace, so `2*pi` gives a number; an empty line gives `[]`. With `'s'` the line comes back as text. Stop abandons the wait. With no prompt to type at (a headless script) it is an error, which `try` can catch.

## Example

```matlab
try
    n = input('How many points? ');
catch
    n = 10;          % nobody to ask: use a default
end
n
```

## See also

[keyboard](keyboard) · [inputdlg](inputdlg)
