# fwrite

Write binary data to an open file.

## Syntax

    count = fwrite(fid, A)
    count = fwrite(fid, A, precision)
    count = fwrite(fid, A, precision, 0, machinefmt)

## Description

`fwrite` writes the elements of `A`, column by column, as `precision` (unsigned 8-bit by default). Values are rounded and clipped to an integer type's range, as MATLAB does. Text is written as its character codes. Returns the number of elements written.

## Example

```matlab
fid = fopen('b.bin', 'w');
n = fwrite(fid, [1.5 2.5 1000], 'uint8')
fclose(fid);
fid = fopen('b.bin'); fread(fid)', fclose(fid);
```

## See also

[fread](fread) · [fopen](fopen) · [fprintf](fprintf)
