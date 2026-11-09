# close

Close figures.

## Syntax

    close
    close(n)
    close all

## Description

`close` closes the current figure. `close(n)` closes figure `n`; `n` can be a vector of numbers. `close all` closes every figure.

Closing a figure frees its number: the next [figure](figure) takes the lowest number no open figure has. The other figures keep theirs. Asking for a figure that is not open is an error.

## Example

```matlab
plot(1:3)
plot(1:4)
close(1)
close all
```

## See also

[figure](figure) · [gcf](gcf) · [clf](clf)
