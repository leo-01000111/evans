# annotation

Draw a line, an arrow, a box or a note over the figure.

## Syntax

    annotation(kind, x, y)
    annotation(kind, dim)
    annotation(..., Name, Value)

## Description

`annotation` draws over the whole figure, in fractions of its width and height from its lower-left corner, so a shape stays put when the axes are zoomed. That is the difference from [text](text), which is tied to the data.

For `'line'`, `'arrow'`, `'doublearrow'` and `'textarrow'`, `x = [x1 x2]` and `y = [y1 y2]` give the start and end. A text arrow writes its `'String'` at the start.

For `'textbox'`, `'rectangle'` and `'ellipse'`, `dim = [x y w h]` gives the lower-left corner, the width and the height. A text box writes its `'String'` inside a framed box.

`'Color'`, `'LineWidth'`, `'FaceColor'`, `'EdgeColor'`, `'BackgroundColor'` and `'FontSize'` are used. Annotations are drawn on screen and in saved files.

## Example

```matlab
plot(1:10, (1:10).^2)
annotation('arrow', [0.4 0.6], [0.6 0.45])
annotation('textbox', [0.15 0.75 0.25 0.08], 'String', 'grows fast')
```

## See also

[text](text) · [xline](xline) · [title](title)
