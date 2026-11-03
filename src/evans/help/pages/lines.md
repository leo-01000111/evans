# lines

MATLAB's line colours as a colour map.

## Syntax

    C = lines
    C = lines(n)

## Description

`lines(n)` returns an n-by-3 matrix of RGB colours: MATLAB's seven default line colours, repeated as needed. `lines` alone gives 256 rows. Pass it to [colororder](colororder) to colour curves as MATLAB does, or to [colormap](colormap) for a map of distinct colours.

## Example

```matlab
C = lines(3)
```

## See also

[colororder](colororder) · [colormap](colormap)
