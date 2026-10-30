# save_system

Write a Simulink model to a file.

## Syntax

    save_system('name')
    save_system('name', 'file.fmdl')
    file = save_system(...)

## Description

`save_system('name')` writes the model to `name.fmdl` in the current folder; with a second argument, to that file, and the model takes the file's name, as in Simulink. The file keeps parameters as they were written, so a Gain of `Kp` is still `Kp` when the file is opened again.

## Example

```matlab
new_system('saved');
add_block('Constant', 'saved/c');
file = save_system('saved')
```

## See also

[load_system](load_system) · [new_system](new_system)
