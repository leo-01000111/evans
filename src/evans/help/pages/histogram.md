# histogram

Count how many values fall in each bin and draw the counts as bars.

## Syntax

    histogram(x)
    histogram(x, nbins)
    histogram(x, edges)
    h = histogram(...)

## Description

`histogram(x)` sorts the elements of `x` into bins of equal width chosen from the data and draws one bar for each. `histogram(x, nbins)` uses `nbins` bins over the range of the data, and `histogram(x, edges)` uses the bin edges you give, a vector in increasing order. `NaN` and infinite values are ignored.

With an output, `h = histogram(...)` returns a struct with the fields `Values` (the count in each bin), `BinEdges`, `NumBins`, `BinWidth` and `Data`. `histcounts` returns the counts without drawing anything, and `hist` is the older command that returns counts and bin centres.

Only the counts are drawn; `'Normalization'` and the other name-value options are not used.

## Example

```matlab
rng(1); x = randn(1, 500);
h = histogram(x, 12);
h.NumBins
xlabel('x'); ylabel('count')
```

## See also

[bar](bar) · [mean](mean) · [rng](rng)
