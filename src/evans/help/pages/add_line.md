# add_line

Wire one block's output to another block's input.

## Syntax

    add_line('model', 'from/1', 'to/2')

## Description

`add_line(system, 'from/k', 'to/m')` draws a wire from output port `k` of block `from` to input port `m` of block `to`, numbered from 1 as in Simulink. Ports may also be named, `'Sum1/in2'`. The system is a model, or `'model/sub'` to wire inside a subsystem. An input takes one wire; `delete_line(system, 'from/k', 'to/m')` removes one.

## Example

```matlab
new_system('m');
add_block('Constant', 'm/a', 'Value', '2');
add_block('Constant', 'm/b', 'Value', '5');
add_block('Sum', 'm/s', 'Inputs', '+-');
add_block('Out1', 'm/y');
add_line('m', 'a/1', 's/1');
add_line('m', 'b/1', 's/2');
add_line('m', 's/1', 'y/1');
out = sim('m', 1);
out.yout(end)
```

## See also

[add_block](add_block) · [new_system](new_system)
