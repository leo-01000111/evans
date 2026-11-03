# pause

Wait for a while.

## Syntax

    pause(t)
    pause
    pause on
    pause off
    state = pause('query')

## Description

`pause(t)` waits `t` seconds; the Stop button ends the wait. A bare `pause` (wait for a key press in MATLAB) does not wait in Evans. `pause off` makes every later pause return at once, which is handy for running a script with animations quickly; `pause on` undoes it.

## Example

```matlab
tic; pause(0.2); toc
```

## See also

[tic](tic) · [toc](toc)
