# zlabel

Label the z axis of 3-D axes.

## Syntax

    zlabel(text)

## Description

`zlabel(text)` labels the vertical axis of the current 3-D axes, as [xlabel](xlabel) and [ylabel](ylabel) label the other two. Typed at a later prompt, it reaches the figure drawn last.

## Example

```matlab
surf(peaks(20)); xlabel('x'); ylabel('y'); zlabel('height')
```

## See also

[xlabel](xlabel) · [ylabel](ylabel) · [zlim](zlim) · [view](view)
