# get_param

Read a block's parameter or a model's setting, as text.

## Syntax

    value = get_param('model/block', 'Parameter')
    value = get_param('model', 'StopTime')

## Description

`get_param('model/block', name)` returns a block parameter as text, the way it was written: `'Kp'` for a Gain of `Kp`, `'2'` for a Gain of 2. A block inside a subsystem is named by its path, `'model/subsystem/block'`. Parameter names may be Evans's own (`gain`, `num`), the label in the block's dialog, or Simulink's (`Gain`, `Numerator`, `UpperLimit`, `SampleTime`). `'BlockType'` gives the block's type, `'DialogParameters'` a struct naming every parameter, and `'Position'` where it sits.

On a model, `get_param` reads the run settings: `StopTime`, `Solver`, `MaxStep` (`FixedStep`), `RelTol` and `AbsTol`.

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
get_param('loop/K', 'Gain')
get_param('loop/G', 'Denominator')
get_param('loop', 'StopTime')
```

## See also

[set_param](set_param) · [find_system](find_system)
