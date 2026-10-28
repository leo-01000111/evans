# filtfilt

Zero-phase digital filtering: filter forwards, then backwards.

## Syntax

    y = filtfilt(b, a, x)
    y = filtfilt(sos, g, x)
    y = filtfilt(d, x)

## Description

`filtfilt` runs the filter `b/a` over `x`, then over the result reversed, so the output has no phase lag and the magnitude response is squared. It pads the ends as MATLAB does (an odd reflection of `3*(max(length(a), length(b)) - 1)` samples, with matching initial conditions), so the result agrees with MATLAB's to rounding. A matrix is filtered column by column.

A second-order-section matrix `sos` with gains `g`, and a filter `d` from `designfilt`, work too. The data must be longer than three times the filter order.

## Example

```matlab
[b, a] = butter(4, 0.1);
t = 0:0.01:2;
x = sin(2*pi*t) + 0.2*randn(size(t));
y = filtfilt(b, a, x);
```

## See also

[fir1](fir1)
