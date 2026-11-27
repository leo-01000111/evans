# save

Save workspace variables to a file.

## Syntax

    save filename
    save filename var1 var2 ...
    save(filename, 'var1', 'var2', ...)
    save filename -append
    save filename -v7.3
    save filename var -ascii

## Description

`save` writes workspace variables to `filename`, resolved from the folder of the running script (the current folder at the prompt). With no variable names it saves them all; with names, only those. A name may contain the wildcards `*`, `?` and `[...]`, so `save('d.mat', 'a*')` saves every variable that starts with `a`. A name with no wildcard that is not a variable stops with "Variable 'x' not found." The default file name is `matlab.mat`, and `.mat` is added to a name with no extension.

The default is a version 5 MAT-file. `-v7.3` writes an HDF5 MAT-file instead, and `-append` adds variables to an existing file, replacing those with the same name and keeping the others. Variables can be numbers, complex numbers, character vectors, cells and structs.

`-ascii` writes the numeric variables as plain text, eight significant digits in exponent form, with the variables stacked as rows. No `.mat` is added then, and `load` reads such a file back as a matrix.

Limits: strings in double quotes, function handles, tables and other objects cannot be saved. The failure message is misleading: it says "Variable 'f' not found." although the variable exists.

## Example

```matlab
a = [1 2; 3 4];
name = 'run 7';
save('evans_demo.mat', 'a', 'name');
clear a name
S = load('evans_demo.mat');
size(S.a)
S.name
delete('evans_demo.mat');
```

The file is read back as the struct `S`, whose field `a` is 2 by 2 and whose field `name` is `run 7`; the last line removes the file.

## See also

[load](load) · [who](who) · [clear](clear) · [delete](delete)
