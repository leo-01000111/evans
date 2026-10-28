# fclose

Close an open file.

## Syntax

    fclose(fid)
    fclose('all')
    status = fclose(...)

## Description

`fclose(fid)` closes a file opened with `fopen`; `status` is `0` when it worked. `fclose('all')` closes every open file. A file left open keeps what was written in a buffer, so close a file before reading it back.

## Example

```matlab
fid = fopen('a.txt', 'w');
fprintf(fid, 'hello\n');
status = fclose(fid)
```

## See also

[fopen](fopen) · [fprintf](fprintf)
