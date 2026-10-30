# find_system

List the blocks of a model, or the ones of one type.

## Syntax

    paths = find_system('model')
    paths = find_system('model', 'BlockType', 'Gain')

## Description

`find_system('model')` returns a column cell of the model's name and every block's path, including blocks inside subsystems. With `'BlockType'` (Evans's or Simulink's name for the block) or `'Name'`, only the matching blocks are listed.

## Example

```matlab
new_system('m');
add_block('Gain', 'm/g1');
add_block('Gain', 'm/g2');
add_block('Constant', 'm/c');
find_system('m', 'BlockType', 'Gain')
```

## See also

[get_param](get_param) · [add_block](add_block)
