# dir

List the files and folders in a folder.

## Syntax

    dir
    dir name
    listing = dir(name)

## Description

`dir` prints the contents of the current folder; `name` may be a folder or a pattern such as `*.csv`. With an output it returns an n×1 struct array with fields `name`, `folder`, `date`, `bytes`, `isdir` and `datenum`.

## Example

```matlab
fid = fopen('a.csv', 'w'); fclose(fid);
d = dir('*.csv');
d(1).name
```

## See also

[exist](exist)
