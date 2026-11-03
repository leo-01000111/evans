# title

Set the title of the current axes.

## Syntax

    title(text)

## Description

`title(text)` puts `text` above the current axes, replacing any title already there, including the default one of a [step](step) or [bode](bode) plot. With a [subplot](subplot) grid it titles the selected cell.

`text` is a character vector or string. A cell array of strings, which in MATLAB gives a title over several lines, is joined into one line with spaces. Extra arguments after the text, such as name-value pairs for the font, are ignored. To put a number in the title, build the text first with [sprintf](sprintf) or [num2str](num2str).

Call `title` after the plot command. A plot command without [hold](hold) starts new axes, so a title set before it is lost, as in MATLAB. Typed at a later prompt, it reaches the figure drawn last, while that figure is open.

`title(t, text)`, with `t` from [tiledlayout](tiledlayout), titles the whole layout; with axes from [nexttile](nexttile), that tile.

## Example

```matlab
G = tf(10, [1 3 10]);
K = 2;
step(feedback(K*G, 1)); title(sprintf('Closed loop, K = %g', K))
```

## See also

[xlabel](xlabel) · [ylabel](ylabel) · [legend](legend) · [subplot](subplot) · [tiledlayout](tiledlayout) · [sprintf](sprintf)
