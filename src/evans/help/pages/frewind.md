# frewind

Go back to the start of an open file.

## Syntax

    frewind(fid)

## Description

`frewind(fid)` is `fseek(fid, 0, 'bof')`: the next read starts again from the first byte.

## Example

```matlab
fid = fopen('t.txt', 'w'); fprintf(fid, 'first\nsecond\n'); fclose(fid);
fid = fopen('t.txt');
fgetl(fid);
frewind(fid);
fgetl(fid)
fclose(fid);
```

## See also

[fseek](fseek) · [ftell](ftell) · [fopen](fopen)
