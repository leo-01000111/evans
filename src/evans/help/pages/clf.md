# clf

Clear the current figure.

## Syntax

    clf

## Description

`clf` removes everything from the current figure: its curves, titles and labels, so the next plot starts on empty axes. The figure itself stays. Use [close](close) to remove the figure altogether.

## Example

```matlab
plot(1:5); title('first')
clf
plot(5:-1:1); title('second')
```

## See also

[close](close) · [figure](figure) · [hold](hold) · [gcf](gcf)
