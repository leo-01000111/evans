# fscanf

Read formatted numbers or text from an open file.

## Syntax

    A = fscanf(fid, format)
    A = fscanf(fid, format, sizeA)
    [A, count] = fscanf(...)

## Description

`fscanf` applies `format` (`'%f'`, `'%d %d'`, `'%s'`) again and again until the file ends or a field does not match, and returns what it read as a column. `sizeA` limits the count: `n`, `Inf`, or `[m n]` to fill an m-row matrix column by column. `count` is the number of values read.

With only `%s` and `%c` conversions the result is text. Evans returns that text as a row; a `[m n]` size for text is not supported.

## Example

```matlab
fid = fopen('p.txt', 'w'); fprintf(fid, '1 2\n3 4\n5 6\n'); fclose(fid);
fid = fopen('p.txt');
A = fscanf(fid, '%f %f', [2 Inf])
fclose(fid);
```

## See also

[textscan](textscan) · [fopen](fopen) · [fprintf](fprintf)
