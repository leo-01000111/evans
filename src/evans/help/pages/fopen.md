# fopen

Open a file and return its file identifier.

## Syntax

    fid = fopen(filename)
    fid = fopen(filename, permission)
    [fid, msg] = fopen(...)

## Description

`permission` is `'r'` (the default), `'w'`, `'a'`, `'r+'`, `'w+'` or `'a+'`, with an optional `'t'`. The identifier is 3 or more; identifiers 1 and 2 are the screen and the error stream. When the file cannot be opened, `fid` is `-1` and `msg` says why.

Write with `fprintf(fid, ...)` or `fwrite`, read with `fgetl`, `fgets`, `fscanf`, `textscan` or `fread`, and close with `fclose`. Encodings other than UTF-8 and the usual 8-bit ones are not supported.

## Example

```matlab
fid = fopen('notes.txt', 'w');
fprintf(fid, 'line %d\n', 1:3);
fclose(fid);
fid = fopen('notes.txt');
first = fgetl(fid)
fclose(fid);
```

## See also

[fclose](fclose) · [fgetl](fgetl) · [fprintf](fprintf) · [textscan](textscan)
