# addpath

Add folders to the search path for function files.

## Syntax

    addpath(folder)
    addpath(folder1, folder2, ...)
    addpath(folder, '-end')
    addpath('folder1;folder2')

## Description

`addpath(folder)` puts `folder` at the front of the search path, so that a function file `name.m` kept there is found by `name(...)` from any folder. The current folder is searched first, then the path in order. Several folders can be given as separate arguments, or in one text separated by the platform's path separator (`;` on Windows, `:` elsewhere). A folder already on the path moves to the new position.

`'-end'` among the arguments puts the folders at the end of the path instead of the front. Any other argument that starts with `-`, such as `'-begin'` or `'-frozen'`, is skipped without effect.

A relative folder is turned into a full path when `addpath` runs, so a later `cd` does not change what was added. Unlike the current folder (see [cd](cd)), the path stays for the rest of the session.

`rmpath(folder)` takes a folder off the path again; a folder that is not on it is ignored.

A folder that does not exist is not added: `addpath('no_such_folder')` prints "Warning: Name is nonexistent or not a directory:" and the full path. A cell array or a number, `addpath({'lib'})` or `addpath(5)`, stops with "Arguments must contain a character vector."

Limits of Evans:

- `addpath` returns nothing: `x = addpath('lib')` gives `x = []`, not the old path.
- Subfolders are not added; `genpath`, `path` and `pathsep` do not exist in Evans.

## Example

```matlab
addpath(pwd);
rmpath(pwd);
disp('path changed and restored')
```

A typical use, with a folder `lib` beside the script holding `myfn.m`:

```
addpath('lib')
myfn(2)
```

## See also

[cd](cd) · [pwd](pwd) · [which](which) · [exist](exist)
