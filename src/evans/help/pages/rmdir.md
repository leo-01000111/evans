# rmdir

Remove a folder.

## Syntax

    rmdir folder
    rmdir(folder, 's')
    [status, msg, msgID] = rmdir(...)

## Description

Removes an empty folder. `'s'` removes it with everything inside it; there is no undo.

## Example

```matlab
mkdir tmpdir
rmdir tmpdir
exist('tmpdir', 'dir')
```

## See also

[mkdir](mkdir) · [delete](delete)
