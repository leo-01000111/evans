# sgtitle

Add a title over a whole grid of subplots.

## Syntax

    sgtitle(txt)

## Description

`sgtitle(txt)` puts `txt` as one title above all the axes of the figure, over the titles that [title](title) gives each axes. It is meant for a figure made with [subplot](subplot) or [tiledlayout](tiledlayout), where the axes each tell part of one story.

On a figure with a single axes it works as a title for the figure. `txt` is a character vector or a string.

## Example

```matlab
t = 0:0.1:6;
subplot(2, 1, 1); plot(t, sin(t)); title('sine')
subplot(2, 1, 2); plot(t, cos(t)); title('cosine')
sgtitle('Two phases')
```

## See also

[title](title) · [subplot](subplot) · [tiledlayout](tiledlayout) · [xlabel](xlabel)
