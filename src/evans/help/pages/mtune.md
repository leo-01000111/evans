# mtune

Find the proportional gain that makes the Nichols curve of `K*G` tangent to a closed-loop M-contour.

## Syntax

    C = mtune(G, M)
    C = mtune(G, M, 'abs')

## Description

`C = mtune(G, M)` returns a constant controller `C = K` such that the peak of the closed-loop magnitude `|KG/(1+KG)|` is exactly `M` dB. That is the gain at which the Nichols curve of `K*G` just touches the M dB contour of the chart without crossing it. `M` is in dB because that is how the Nichols contours are labelled.

`mtune(G, M, 'abs')` takes `M` as a plain magnitude instead (`1.3` rather than `2.3`).

The peak grows with `K`, so the answer is the largest stable gain whose peak is still `M`. When no gain does it (an integrating plant is already at 0 dB at DC, so a contour below 0 dB is never reached), `mtune` stops with an error that says so.

The result is attached as `C.tuning`: `C.tuning.K`, `C.tuning.peak_db` and `C.tuning.omega_peak`, the frequency where the curve touches the contour.

## Example

```matlab
G = tf(1, [1 3 3 1]);
C = mtune(G, 2.3);
nichols(C*G); ngrid
disp(C.tuning.omega_peak)
```

## See also

[nichols](nichols) · [pidtune](pidtune) · [margin](margin) · [feedback](feedback)
