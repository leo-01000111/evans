# movefile

Move or rename a file or a folder.

## Syntax

    movefile source destination
    status = movefile(source, destination)
    [status, msg, msgID] = movefile(...)

## Description

Moves `source` to `destination`; in the same folder that is a rename. With outputs, a failure sets `status` to false and `msg` instead of stopping with an error.

## Example

```matlab
fclose(fopen('a.txt', 'w'));
movefile('a.txt', 'renamed.txt');
exist('renamed.txt', 'file')
```

## See also

[copyfile](copyfile) · [delete](delete)
