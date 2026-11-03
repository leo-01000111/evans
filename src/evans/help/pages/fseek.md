# fseek

Move to a position in an open file.

## Syntax

    status = fseek(fid, offset)
    status = fseek(fid, offset, origin)

## Description

Moves `offset` bytes from `origin`: `'bof'` (the start, the default), `'cof'` (the current position) or `'eof'` (the end); `-1`, `0` and `1` mean the same. A negative `offset` moves back. Returns 0, or -1 when the position would be before the start of the file, or past its end in a file open only for reading.

## Example

```matlab
fid = fopen('t.txt', 'w'); fprintf(fid, 'abcdef'); fclose(fid);
fid = fopen('t.txt');
fseek(fid, -2, 'eof');
rest = fgetl(fid)
fclose(fid);
```

## See also

[ftell](ftell) · [frewind](frewind) · [fread](fread)
