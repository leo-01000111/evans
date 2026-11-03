# view

Set the angle 3-D axes are seen from.

## Syntax

    view(az, el)
    view([az el])
    view(2)
    view(3)
    [az, el] = view

## Description

`view(az, el)` turns the current axes to azimuth `az` and elevation `el`, in degrees, as MATLAB measures them: the azimuth from the negative y axis, counter-clockwise seen from above, and the elevation up from the x-y plane.

`view(3)` is the default 3-D view, `view(-37.5, 30)`. `view(2)` looks straight down, which turns a [surf](surf) into a coloured map. `view` on 2-D axes with an angle other than straight down draws them in 3-D.

`[az, el] = view` returns the angle set for the current axes. The angle the mouse leaves the axes at is not read back.

## Example

```matlab
surf(peaks(25)); view(60, 20)
```

## See also

[surf](surf) · [plot3](plot3) · [zlabel](zlabel)
