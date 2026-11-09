# stairs

Plot a sequence as a staircase, each value held until the next.

## Syntax

    stairs(y)
    stairs(x, y)
    stairs(x, y, spec)

## Description

`stairs(y)` draws the elements of `y` as a step function: the line stays level at each value and jumps straight up or down at the next point. `stairs(x, y)` puts the steps at the values of `x`. It shows what a zero-order hold does to a sampled signal, as in the input a digital controller sends to a plant.

`spec` is a line specification such as `'r'` or `'r--'`. With [hold](hold) on, several `stairs` calls share the axes. A matrix is drawn one staircase for each column.

## Example

```matlab
t = 0:0.5:5;
u = round(2*sin(t));
stairs(t, u); xlabel('t (s)'); ylabel('u')
```

## See also

[stem](stem) · [plot](plot) · [bar](bar)
