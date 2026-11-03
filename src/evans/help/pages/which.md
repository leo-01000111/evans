# which

Where a name comes from: a variable, a file, or Evans itself.

## Syntax

    which name
    s = which(name)

## Description

`which name` says what a call to `name` would run: a variable, a local function of the running script, a `.m` file on the path (with its full path), or `built-in (Evans)` for Evans's own functions. With an output, the answer is returned as text, `''` when the name is unknown.

Evans does not support `which -all`.

## Example

```matlab
which sin
x = 3;
which x
```

## See also

[exist](exist) · [who](who)
