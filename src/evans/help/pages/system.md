# system

Run an operating-system command.

## Syntax

    status = system(command)
    [status, cmdout] = system(command)
    [status, cmdout] = system(command, '-echo')

## Description

`system` runs `command` in the system shell, from the current folder, and returns its exit status (0 for success). With two outputs the command's output is returned as text instead of printed, unless `'-echo'` asks for both. A command ending in `&` is started in the background. The Stop button ends a command that is still running.

## Example

```matlab
[status, out] = system('echo hello')
```

## See also

[getenv](getenv) · [computer](computer)
