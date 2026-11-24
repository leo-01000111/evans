# pwd

Return the current folder.

## Syntax

    pwd
    folder = pwd

## Description

`pwd` returns the full path of the current folder as a row of characters (`class` is `char`, and it has one row). At the console `pwd` prints it as `ans`. It is the folder `cd` last set during the run; if `cd` has not been called, it is the folder of the script that is running, or the folder Evans was started in.

`pwd` takes no argument: `pwd(1)` stops with an internal `TypeError` message. It never fails.

The current folder lasts one run (see [cd](cd)): a `cd` typed on one line is not seen by `pwd` on the next line.

## Example

```matlab
p = pwd;
ischar(p)
size(p, 1)
```

Both lines print 1. The text of the path depends on the machine, so it is not shown here.

## See also

[cd](cd) · [dir](dir) · [ls](ls) · [which](which)
