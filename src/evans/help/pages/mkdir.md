# mkdir

Make a folder.

## Syntax

    mkdir folder
    mkdir(parent, folder)
    [status, msg, msgID] = mkdir(...)

## Description

Makes `folder`, inside the current folder unless the path says otherwise, with any missing parents. A folder that already exists gives a warning, not an error.

## Example

```matlab
mkdir results
exist('results', 'dir')
```

## See also

[rmdir](rmdir) · [dir](dir)
