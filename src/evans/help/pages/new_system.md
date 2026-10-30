# new_system

Create an empty Simulink model, to build with add_block and add_line.

## Syntax

    new_system('name')

## Description

`new_system('name')` makes an empty model called `name`, held in this session until [save_system](save_system) writes it to `name.fmdl`. Add blocks with [add_block](add_block) and wire them with [add_line](add_line); [open_system](open_system) puts it on the Model tab. `close_system('name')` forgets it.

## Example

```matlab
new_system('loop');
add_block('Step', 'loop/r', 'StepTime', '0');
add_block('Gain', 'loop/K', 'Gain', 'Kp');
add_block('Transfer Fcn', 'loop/G', 'Denominator', '[1 1]');
add_block('Out1', 'loop/y');
add_line('loop', 'r/1', 'K/1');
add_line('loop', 'K/1', 'G/1');
add_line('loop', 'G/1', 'y/1');
Kp = 2;
out = sim('loop', 5);
out.yout(end)
```

## See also

[add_block](add_block) · [add_line](add_line) · [save_system](save_system) · [load_system](load_system)
