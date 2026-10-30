# sim

Run a Simulink model and return its output: the times, the top-level Outports, and every To Workspace block.

## Syntax

    out = sim('model')
    out = sim('model', Tfinal)
    out = sim('model', 'StopTime', '20', 'Solver', 'ode15s')
    r = sim(model, Tfinal)

## Description

`out = sim('model')` runs the model named `model`: the one on the Model tab if it has that name, one loaded with [load_system](load_system) or [new_system](new_system), or else `model.fmdl` from the current folder or the path. It runs with the model's own settings (stop time, solver, step, tolerances), which the Model tab's toolbar shows and [set_param](set_param) changes. Name-value pairs override them for this run: `StopTime`, `Solver`, `MaxStep` (or `FixedStep`), `RelTol` and `AbsTol`. A number after the name is the stop time.

Block parameters written as workspace variables or expressions, such as a Gain of `Kp` or a frequency of `2*pi*f`, are evaluated in the workspace when the model runs. A loop that sets `Kp` and calls `sim` is therefore a parameter sweep.

`out` is a structure like Simulink's `SimulationOutput`:

- `out.tout`: the times, a column.
- `out.yout`: the top-level Outports' signals, one column each, in port order, when the model has any.
- one field per To Workspace block, named by its variable name and shaped by its save format: a matrix (`Array`), a struct with `time` and `signals.values` (`Structure With Time`), or a struct with `Time` and `Data` (`Timeseries`, which `plot` draws directly).

A run started with the Model tab's Run button leaves the same structure in the workspace as `out`.

`r = sim(model, Tfinal)`, given a model object rather than a name (the Model tab's model is in the workspace as `model`), returns the Python result instead: `r.t`, `r.trace('G')`, `r.signals`, `r.states` and `r.warnings`.

To get a transfer function out of the model instead of a time response, use [linearize](linearize).

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
for Kp = [1 4]
    out = sim('loop', 5);
    fprintf('Kp = %g: y(5) = %.4f\n', Kp, out.yout(end));
end
```

## See also

[new_system](new_system) · [set_param](set_param) · [get_param](get_param) · [linearize](linearize) · [lsim](lsim)
