# semilogy

Line plot with a logarithmic y axis and a linear x axis.

## Syntax

    semilogy(y)
    semilogy(x, y)
    semilogy(x, y, spec)
    semilogy(x1, y1, spec1, x2, y2, spec2, ...)

## Description

`semilogy` takes the same arguments as [plot](plot) and draws the same curves, with the y axis on a log scale. It suits a quantity that falls or grows over several decades, such as an error against iteration number, or a decay envelope.

Points with `y` less than or equal to zero cannot be shown on a log axis and are left out of the drawing. With [hold](hold) on, several `semilogy` calls share the axes.

## Example

```matlab
k = 0:20;
err = 0.5.^k;
semilogy(k, err, 'o-'); xlabel('iteration'); ylabel('error')
```

## See also

[semilogx](semilogx) · [loglog](loglog) · [plot](plot)
