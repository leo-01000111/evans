# delete_block

Remove a block, and its wires, from a model.

## Syntax

    delete_block('model/name')

## Description

`delete_block('model/name')` removes the block and every wire into or out of it. Inside a subsystem, name it by its path.

## Example

```matlab
new_system('m');
add_block('Constant', 'm/c');
add_block('Gain', 'm/g');
add_line('m', 'c/1', 'g/1');
delete_block('m/g');
find_system('m')
```

## See also

[add_block](add_block) · [find_system](find_system)
