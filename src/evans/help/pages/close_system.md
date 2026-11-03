# close_system

Close a model that is loaded in the console.

## Syntax

    close_system(model)
    close_system

## Description

Forgets the model loaded with [load_system](load_system) or made with [new_system](new_system); unsaved changes are dropped. With no argument, every loaded model is closed. Save first with [save_system](save_system) to keep the changes.

## Example

```matlab
new_system('demo');
close_system('demo')
```

## See also

[new_system](new_system) · [load_system](load_system) · [save_system](save_system)
