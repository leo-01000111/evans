# load_system

Load a Simulink model from its file without showing it.

## Syntax

    load_system('name')
    load_system('file.fmdl')

## Description

`load_system('name')` reads `name.fmdl` from the current folder or the path, so that [get_param](get_param), [set_param](set_param) and [sim](sim) can use it by name. A model is named after its file. Loading is also what `sim('name')` does by itself when the model is not loaded yet. `close_system('name')` forgets the loaded copy; the file is not touched.

## Example

```matlab
new_system('m');
add_block('Constant', 'm/c', 'Value', '3');
add_block('Out1', 'm/y');
add_line('m', 'c/1', 'y/1');
save_system('m');
close_system('m');
load_system('m');
get_param('m/c', 'Value')
```

## See also

[open_system](open_system) · [save_system](save_system) · [sim](sim)
