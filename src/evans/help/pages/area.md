# area

Fill the area under a curve, or stack several on top of each other.

## Syntax

    area(y)
    area(x, y)
    area(x, Y)
    area(..., basevalue)
    area(..., Name, Value)

## Description

`area(x, y)` draws `y` against `x` and fills the region between the curve and zero. `area(y)` uses `1:length(y)` for `x`.

When `Y` is a matrix, each column is one area and they are stacked: the second column is drawn on top of the first, so the top edge of the stack is the sum of the columns. This is how a total split into parts is usually shown.

`basevalue` moves the floor the areas are filled down to (0 by default). `'FaceColor'`, `'FaceAlpha'` and `'DisplayName'` are used.

## Example

```matlab
t = 0:10;
area(t, [t; 0.5*t; 2*ones(1, 11)]'); legend('a', 'b', 'c', 'Location', 'northwest')
```

## See also

[plot](plot) · [fill](fill) · [bar](bar)
