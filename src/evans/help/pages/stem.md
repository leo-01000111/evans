# stem

Plot a sequence as vertical lines ending in markers.

## Syntax

    stem(y)
    stem(x, y)
    stem(x, y, spec)

## Description

`stem(y)` draws a line from zero up to each element of `y`, ending in a marker, at 1, 2, 3 and so on; `stem(x, y)` puts them at the values of `x`. It is the plot for a discrete-time signal, such as a sampled impulse response or the output of a difference equation.

`spec` is a line specification such as `'r'` or `'r--'`: the colour and line style are used. With [hold](hold) on, several `stem` calls share the axes. For a continuous curve use [plot](plot), and for a signal held between samples use [stairs](stairs).

## Example

```matlab
n = 0:15;
y = 0.8.^n .* cos(0.6*n);
stem(n, y); xlabel('n'); ylabel('y[n]')
```

## See also

[stairs](stairs) · [plot](plot) · [bar](bar) · [scatter](scatter)
