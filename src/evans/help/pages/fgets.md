# fgets

Read one line of a text file, keeping its newline.

## Syntax

    line = fgets(fid)

## Description

`fgets` is [fgetl](fgetl) without removing the newline at the end of the line. At the end of the file it returns `-1`.

Evans does not support the `nchar` argument.

## Example

```matlab
fid = fopen('t.txt', 'w'); fprintf(fid, 'one\ntwo\n'); fclose(fid);
fid = fopen('t.txt');
line = fgets(fid)
fclose(fid);
```

## See also

[fgetl](fgetl) · [fopen](fopen) · [feof](feof)
