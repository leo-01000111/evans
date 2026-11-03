# ftell

The current position in an open file, in bytes.

## Syntax

    position = ftell(fid)

## Description

Counted from 0 at the start of the file. Use it with [fseek](fseek) to come back to a place you have read up to.

## Example

```matlab
fid = fopen('t.txt', 'w'); fprintf(fid, 'abc\ndef\n'); fclose(fid);
fid = fopen('t.txt');
fgetl(fid);
ftell(fid)
fclose(fid);
```

## See also

[fseek](fseek) · [frewind](frewind) · [fopen](fopen)
