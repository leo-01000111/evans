# ispc

Whether Evans is running on Windows.

## Syntax

    tf = ispc

## Description

True on Windows. Use it, with [ismac](ismac) and [isunix](isunix), to branch on the platform, for paths or commands that differ.

## Example

```matlab
if ispc
    disp('Windows')
else
    disp('not Windows')
end
```

## See also

[ismac](ismac) · [isunix](isunix) · [computer](computer)
