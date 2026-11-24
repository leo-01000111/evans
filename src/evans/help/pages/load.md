# load

Load variables from a file into the workspace.

## Syntax

    load filename
    load filename var1 var2 ...
    load(filename)
    S = load(filename)
    S = load(filename, 'var1', ...)

## Description

`load` reads a `.mat` file written by [save](save), or a text file of numbers. A relative `filename` is taken from the folder of the running script (the current folder at the prompt). The default is `matlab.mat`, and `.mat` is added when the name as given is not a file. A missing file stops with "Unable to find file or directory 'name'."

Without an output, the variables go into the workspace, replacing those with the same name. With `S = load(...)` they come back as the fields of a struct and the workspace is untouched. Names after the file name limit what is read, and may use `*`, `?` and `[...]`.

Version 5 and version 7.3 (HDF5) MAT-files are both read. For a version 7.3 file, a variable of a kind Evans cannot read is skipped with a "Warning:" line.

A file that is not a `.mat` is read as a text file of numbers: with an output you get the matrix; without one the matrix goes into a variable named after the file, so `load data.txt` creates `data`. Characters that are not valid in a name become `_`.

Limits: integer and logical variables read from a version 5 file come back as `double`. Single-precision values stay `single`.

## Example

```matlab
v = [10 20 30];
save('evans_load.mat', 'v');
clear v
load evans_load.mat
v
delete('evans_load.mat');
```

After `load`, the variable `v` is back in the workspace and prints as `10 20 30`; the file is then deleted.

## See also

[save](save) · [readmatrix](readmatrix) · [fileread](fileread) · [delete](delete)
