# add_block

Add a block to a model.

## Syntax

    add_block('library/path/Block', 'model/name')
    add_block('Block', 'model/name', 'Parameter', value, ...)

## Description

`add_block(source, 'model/name')` adds a block named `name`. The source is Simulink's library path (`'simulink/Math Operations/Gain'`) or just the block's name: only the last part is read, and Simulink's names (`'Transfer Fcn'`, `'Sine Wave'`, `'To Workspace'`, `'Out1'`) are mapped to Evans's blocks. Name-value pairs set its parameters, as [set_param](set_param) does; `'Position'`, `[left top right bottom]`, places it. Without one it goes to the right of the blocks already there.

A destination such as `'model/sub/name'` adds the block inside the subsystem `sub`.

## Example

```matlab
new_system('m');
add_block('simulink/Sources/Sine Wave', 'm/s', 'Frequency', '2*pi');
add_block('simulink/Sinks/Out1', 'm/y');
add_line('m', 's/1', 'y/1');
out = sim('m', 1);
max(out.yout)
```

## See also

[add_line](add_line) · [delete_block](delete_block) · [new_system](new_system)
