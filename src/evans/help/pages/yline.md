# yline

Draw a horizontal line across the axes at a given y.

## Syntax

    yline(y)
    yline(y, linespec)
    yline(y, linespec, label)
    yline(..., Name, Value)

## Description

`yline(y)` draws a horizontal line across the full width of the axes at `y`: a set-point, a limit or a tolerance band. `y` can be a vector, for one line at each value. It takes the same arguments as [xline](xline).

## Example

```matlab
t = linspace(0, 10, 300);
plot(t, 1 - exp(-t).*cos(3*t))
yline([0.98 1.02], ':', {'-2%', '+2%'})
```

## See also

[xline](xline) · [plot](plot)
