# save_system

Write a Simulink model to a file.

## Syntax

    save_system('name')
    save_system('name', 'file.evx')
    file = save_system(...)

## Description

`save_system('name')` writes the model to `name.evx` in the current folder; with a second argument, to that file (a name ending in `.fmdl` writes the older format, for an older Evans), and the model takes the file's name, as in Simulink. The file keeps parameters as they were written, so a Gain of `Kp` is still `Kp` when the file is opened again.

## Example

```matlab
new_system('saved');
add_block('Constant', 'saved/c');
file = save_system('saved')
```

## See also

[load_system](load_system) · [new_system](new_system)
