# figure

Start a new figure, or go back to one by its number.

## Syntax

    figure
    figure(n)
    h = figure

## Description

`figure` makes the next plot command open a new figure instead of adding to the current one. It also turns [hold](hold) off and ends any [subplot](subplot) grid, so the next `subplot` call starts a new grid.

`h = figure` returns the number the next figure will get: the lowest number no open figure has, so 1 for the first.

`figure(n)` makes figure `n` the current one and raises its tab. If there is no figure `n`, the next plot opens it with that number. The next plot command then replaces what figure `n` shows, as in MATLAB; use [hold](hold) to add to it. `n` must be a positive integer. Name-value pairs such as `'Name', 'Bode'` are accepted and ignored. Selecting a tab in the figure area makes that figure current too; [gcf](gcf) returns its number.

You rarely need `figure` between plain plot commands: without `hold on`, each plot already gets a figure of its own. It matters after `hold on` or inside a subplot grid, where the next plot would otherwise land on the existing axes.

## Example

```matlab
G = tf(1, [1 0.4 1]);
step(G); hold on; step(feedback(G, 1))
figure
bode(G)
figure(1)
title('Step responses')
```

## See also

[gcf](gcf) · [close](close) · [clf](clf) · [plot](plot) · [hold](hold) · [subplot](subplot) · [title](title)
