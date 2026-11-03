# axis

Set the limits of both axes of the current plot in one call.

## Syntax

    axis([xmin xmax ymin ymax])
    axis([xmin xmax ymin ymax zmin zmax])
    axis equal
    axis tight
    axis off
    lims = axis

## Description

`axis([xmin xmax ymin ymax])` fixes the x axis to run from `xmin` to `xmax` and the y axis from `ymin` to `ymax`, the same as calling [xlim](xlim) and [ylim](ylim) together. Six limits set the z axis of 3-D axes too.

The limits apply to line plots, time responses such as [step](step), and [pzmap](pzmap). The Bode, Nyquist and root locus windows choose their own ranges and ignore them.

The modes: `axis equal` gives one unit the same length on both axes, so a circle looks round; `axis square` does the same. `axis tight` fits the limits to the data with no margin, and `axis image` is both. `axis ij` puts the y axis's origin at the top, as images are drawn, and `axis xy` back at the bottom. `axis off` hides the axes and `axis on` shows them. `axis auto` lets the limits follow the data again. `axis normal` undoes `equal`.

`lims = axis` returns the current limits, those set or else the data's range.

Call `axis` after the plot command: on the same line, later in the script, or at a later prompt.

## Example

```matlab
G = tf(1, [1 0.3 1]);
step(G); axis([0 20 0 2])
```

## See also

[xlim](xlim) · [ylim](ylim) · [plot](plot) · [grid](grid)
