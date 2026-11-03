# fread

Read binary data from an open file.

## Syntax

    A = fread(fid)
    A = fread(fid, sizeA)
    A = fread(fid, sizeA, precision)
    A = fread(fid, sizeA, precision, 0, machinefmt)
    [A, count] = fread(...)

## Description

`fread` reads bytes as unsigned 8-bit integers by default, or values of `precision`: `'int16'`, `'uint32'`, `'single'`, `'double'`, `'char'` and the rest. They come back as doubles in a column, or shaped by `sizeA` as in [fscanf](fscanf). `machinefmt` is `'ieee-le'` or `'ieee-be'`, else the file's own from [fopen](fopen).

Evans does not support a non-zero skip value or the `'=>'` output-class form.

## Example

```matlab
fid = fopen('b.bin', 'w'); fwrite(fid, [1 -2 300], 'int16'); fclose(fid);
fid = fopen('b.bin');
A = fread(fid, Inf, 'int16')
fclose(fid);
```

## See also

[fwrite](fwrite) · [fopen](fopen) · [fseek](fseek)
