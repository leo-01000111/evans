# zlim

Set or read the limits of the z axis.

## Syntax

    zlim([zmin zmax])
    zlim('auto')
    lims = zlim

## Description

`zlim([zmin zmax])` fixes the range of the z axis of the current 3-D axes, as [xlim](xlim) and [ylim](ylim) do for the others. `zlim('auto')` lets it follow the data again, and `lims = zlim` returns the range.

## Example

```matlab
surf(peaks(20)); zlim([-10 10])
```

## See also

[xlim](xlim) · [ylim](ylim) · [zlabel](zlabel)
