# open_system

Open a Simulink model on the Model tab.

## Syntax

    open_system('name')

## Description

`open_system('name')` loads the model as [load_system](load_system) does and shows it on the Model tab's canvas, where it can be edited and run. The model on the canvas is the one the console's commands then act on: a [set_param](set_param) typed at the prompt redraws it.

## Example

```matlab
new_system('demo');
add_block('Sine Wave', 'demo/s');
add_block('Scope', 'demo/scope');
add_line('demo', 's/1', 'scope/1');
open_system('demo');
```

## See also

[load_system](load_system) · [new_system](new_system) · [sim](sim)
