# exist

Check whether a variable, file, folder or function exists.

## Syntax

    tf = exist(name)
    tf = exist(name, type)

## Description

`exist(name)` is `1` for a workspace variable, `2` for a file (an `.m` file on the path, or any file by its name), `5` for a built-in function, `7` for a folder and `0` otherwise. `type` (`'var'`, `'file'`, `'dir'` or `'builtin'`) checks only that kind. The console's preset values, such as `s`, don't count as variables.

`exist(name, 'class')` isn't supported: Evans has no MATLAB classes.

## Example

```matlab
x = 5;
exist('x')
exist('sin')
exist('no_such_thing')
```

## See also

[who](who)
