# fgetl

Read the next line of a file, without its newline.

## Syntax

    line = fgetl(fid)

## Description

`fgetl` returns the next line as char, with the newline removed. At the end of the file it returns the number `-1`, so a loop reads `while true, line = fgetl(fid); if ~ischar(line), break, end, ... end`. `fgets` keeps the newline.

## Example

```matlab
fid = fopen('two.txt', 'w');
fprintf(fid, 'first\nsecond\n');
fclose(fid);
fid = fopen('two.txt');
while true
    line = fgetl(fid);
    if ~ischar(line), break, end
    disp(line)
end
fclose(fid);
```

## See also

[fopen](fopen)
