# findpeaks

Find the local maxima of a signal.

## Syntax

    [pks, locs] = findpeaks(y)
    [pks, locs] = findpeaks(y, x)
    [pks, locs] = findpeaks(y, fs)
    [pks, locs, w, p] = findpeaks(y, ...)
    [___] = findpeaks(y, Name, Value)
    findpeaks(y, ...)

## Description

`findpeaks` returns the values `pks` of the peaks of the vector `y` and their positions `locs`. A peak is a sample higher than both neighbours. The first and last samples never count. A flat top counts once, at its left edge, and a `NaN` is skipped over. If nothing qualifies, both outputs are empty.

`locs` are sample numbers by default. With a vector `x` of the same length as `y`, they are the matching values of `x`. With a scalar `fs`, `locs` are times in seconds, `(k-1)/fs`. The outputs are rows for a row `y` and columns for a column `y`. A matrix is not searched column by column: it is read as one long signal, column after column, without a message.

The third and fourth outputs are the widths `w` (measured at half the prominence, interpolated) and the prominences `p`.

Options, as name/value pairs, applied in this order:

- `'MinPeakHeight'` keeps peaks above this value.
- `'Threshold'` keeps peaks that exceed both neighbours by at least this much.
- `'MinPeakProminence'` keeps peaks at least this prominent.
- `'MinPeakDistance'` removes the lower of two peaks closer than this, in units of `locs`, keeping the highest first.
- `'SortStr'` is `'none'`, `'ascend'` or `'descend'`, by height.
- `'NPeaks'` keeps the first this many after sorting.

An unknown option name is ignored without a message. With no output, `findpeaks` plots the signal with the peaks marked.

## Example

```matlab
y = [1 3 2 5 4 4 6 1];
[pks, locs] = findpeaks(y)
[pks, locs] = findpeaks(y, 'SortStr', 'descend', 'NPeaks', 2)
[pks, locs, w, p] = findpeaks(y);
p
```

The first call gives `pks` `3 5 6` at `locs` `2 4 7`. The second gives `6 5` at `7 4`. The prominences `p` are `1 1 5`. With `'MinPeakDistance', 3` only `3` (at 2) and `6` (at 7) remain.

## See also

[find](find) · [max](max) · [smoothdata](smoothdata) · [plot](plot)
