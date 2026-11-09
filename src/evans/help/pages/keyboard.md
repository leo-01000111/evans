# keyboard

Give the prompt to the user in the middle of a script.

## Syntax

    keyboard

## Description

Prints a `K>>` prompt and runs what is typed, in the base workspace, until `return` (or `dbcont`) is entered. An error in a typed line is shown and the prompt stays. With no prompt to type at it is an error.

## Example

```matlab
try
    keyboard
catch
    disp('no console to type at')
end
```

## See also

[input](input) · [pause](pause)
