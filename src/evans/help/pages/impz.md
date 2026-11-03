# impz

Impulse response of a digital filter.

## Syntax

    h = impz(b, a)
    h = impz(b, a, n)
    [h, t] = impz(b, a, n, fs)
    h = impz(d, n)
    impz(...)

## Description

The filter's output for a unit impulse. An FIR filter (`a = 1`) gives its taps; an IIR filter needs the number of samples `n`. `n` may also be a vector of sample indices from 0. With `fs`, `t` is in seconds. `d` from [designfilt](designfilt) stands for `b, a`. With no outputs, a stem plot.

## Example

```matlab
h = impz(1, [1 -0.5], 5)'
impz([1 2 1])
```

## See also

[grpdelay](grpdelay)
