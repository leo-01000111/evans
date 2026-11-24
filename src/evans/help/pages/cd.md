# cd

Show or change the current folder.

## Syntax

    cd
    cd(folder)
    cd folder
    old = cd
    old = cd(folder)

## Description

`cd` with no argument prints the current folder; `old = cd` returns it as text instead. `cd(folder)` makes `folder` the current folder, and a relative file name given to `fopen` (checked), and to the other file commands, is taken from it. A relative `folder` is taken from the current folder, so `cd('..')` goes up one level. The command form `cd sub` also works for a plain folder name.

`cd` with a folder returns nothing. `old = cd(folder)` gives `old` the value `[]`, not the previous folder: to keep the old folder to come back to, write `old = cd;` or `old = pwd;` before changing.

An empty name, `cd('')`, does nothing.

Limits of Evans:

- The new folder lasts one run. Each script run, and each line typed at the console, starts in the folder of the running script (or the folder Evans was started in), so a `cd` on one line is gone on the next. Put the `cd` and the commands that need it in the same script or on the same line.
- `cd ..` and `cd .` as a command do not work: Evans stops with "unexpected text after the statement". Write `cd('..')`.
- A folder that does not exist, or is a file, stops with "Cannot CD to name (Name is nonexistent or not a folder)." A number gives the same message with an empty name.
- Two arguments, `cd('a', 'b')`, fail with an internal `TypeError` message.
- `cd` does not change the folder of the Evans process, only the folder Evans uses for file names.

## Example

```matlab
old = pwd;
cd('..');
moved = ~strcmp(old, pwd)
cd(old);
back = strcmp(old, pwd)
```

Both lines print 1: the folder changed, then returned to where it was.

## See also

[pwd](pwd) · [addpath](addpath) · [dir](dir) · [ls](ls) · [mkdir](mkdir)
