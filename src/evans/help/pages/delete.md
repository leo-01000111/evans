# delete

Delete files.

## Syntax

    delete filename
    delete(filename1, filename2, ...)

## Description

`delete` removes files from disk; `*` matches several (`delete *.tmp`). A name that matches nothing gives a warning. The files are deleted, not moved to the recycle bin. [rmdir](rmdir) removes folders.

Evans's delete takes file names only, not graphics objects.

## Example

```matlab
fclose(fopen('old.txt', 'w'));
delete old.txt
exist('old.txt', 'file')
```

## See also

[rmdir](rmdir) · [movefile](movefile) · [dir](dir)
