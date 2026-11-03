# erf

Error function.

## Syntax

    y = erf(x)

## Description

erf(x) = 2/√π ∫₀ˣ e^(−t²) dt, elementwise. A normal distribution's CDF is `0.5*(1 + erf(x/sqrt(2)))`, which [normcdf](normcdf) computes for you.

## Example

```matlab
erf([0 0.5 1 2])
```

## See also

[erfc](erfc) · [erfinv](erfinv) · [normcdf](normcdf)
