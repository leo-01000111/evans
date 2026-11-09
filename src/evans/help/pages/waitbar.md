# waitbar

Show or update a progress bar.

## Syntax

    h = waitbar(x, msg)
    waitbar(x, h, msg)
    close(h)

## Description

`x` is a fraction between 0 and 1. Keep the handle `h` to update the same bar; `close(h)` or `delete(h)` removes it. Headless the bar is not shown and the call only records itself.

## Example

```matlab
h = waitbar(0, 'Working...');
for k = 1:10
    waitbar(k/10, h, sprintf('Step %d of 10', k));
end
close(h)
```

## See also

[inputdlg](inputdlg) · [pause](pause) · [tic](tic)
