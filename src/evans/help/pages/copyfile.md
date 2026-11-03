# copyfile

Copy a file or a folder.

## Syntax

    copyfile source destination
    status = copyfile(source, destination)
    [status, msg, msgID] = copyfile(...)

## Description

Copies `source` (a file, a folder with everything in it, or a `*` pattern) to `destination`. With outputs, a failure sets `status` to false and `msg` instead of stopping with an error.

## Example

```matlab
fid = fopen('a.txt', 'w'); fprintf(fid, 'hello'); fclose(fid);
copyfile('a.txt', 'b.txt');
fid = fopen('b.txt'); fgetl(fid)
fclose(fid);
```

## See also

[movefile](movefile) · [delete](delete) · [mkdir](mkdir)
