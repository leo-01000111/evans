# delete_line

Remove a line between two blocks of a model.

## Syntax

    delete_line(system, 'src/port', 'dst/port')
    delete_line(system, 'src/port')

## Description

Deletes the line from the output port `src/port` (for example `'Gain/1'`) to the input port `dst/port`. With no destination, the first line leaving `src/port` is removed. `system` is a model, or a subsystem as `'model/Subsystem'`.

## Example

```matlab
new_system('m');
add_block('simulink/Sources/Step', 'm/Step');
add_block('simulink/Math Operations/Gain', 'm/Gain');
add_line('m', 'Step/1', 'Gain/1');
delete_line('m', 'Step/1', 'Gain/1');
close_system('m')
```

## See also

[add_line](add_line) · [delete_block](delete_block) · [add_block](add_block)
