# feof

Whether a file's position has reached its end.

## Syntax

    tf = feof(fid)

## Description

True once everything in the file has been read. The usual loop reads lines until `feof` is true.

## Example

```matlab
fid = fopen('t.txt', 'w'); fprintf(fid, 'a\nb\nc\n'); fclose(fid);
fid = fopen('t.txt');
while ~feof(fid)
    disp(fgetl(fid))
end
fclose(fid);
```

## See also

[fgetl](fgetl) · [fopen](fopen) · [frewind](frewind)
