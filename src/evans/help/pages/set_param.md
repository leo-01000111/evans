# set_param

Change block parameters or a model's run settings.

## Syntax

    set_param('model/block', 'Parameter', value, ...)
    set_param('model', 'StopTime', '20')

## Description

`set_param('model/block', name, value)` sets a block parameter; several name-value pairs may follow. A value is a number, or text: text that is a number becomes that number, and other text is a workspace expression, evaluated when the model runs, exactly as if it had been typed in the block's dialog. Names are matched as [get_param](get_param) matches them. If the model is on the Model tab, the canvas redraws.

On a model, `set_param` changes the run settings `StopTime`, `Solver`, `MaxStep`, `RelTol` and `AbsTol`, which the Model tab's toolbar shows.

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
set_param('loop/K', 'Gain', '3');
set_param('loop', 'StopTime', '8');
out = sim('loop');
out.yout(end)
```

## See also

[get_param](get_param) · [sim](sim)
