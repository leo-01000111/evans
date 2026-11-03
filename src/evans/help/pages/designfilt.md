# designfilt

Design a digital filter from its specification.

## Syntax

    d = designfilt(response, Name, Value, ...)

## Description

`response` is `'lowpassiir'`, `'highpassiir'` or `'bandpassiir'` (Butterworth, given `'FilterOrder'` and `'HalfPowerFrequency'`, or `'HalfPowerFrequency1'` and `'2'` for a band), or `'lowpassfir'` or `'highpassfir'` (windowed, given `'FilterOrder'`, `'CutoffFrequency'` and optionally `'Window'`). Frequencies are relative to Nyquist unless `'SampleRate'` gives the rate in Hz.

Apply `d` with `filter(d, x)` or `filtfilt(d, x)`, and inspect it with `freqz(d)`, `impz(d)` and `grpdelay(d)`. `d.Coefficients` gives an FIR filter's taps. An IIR filter is kept as second-order sections, which stay accurate where one multiplied-out `b/a` would not.

## Example

```matlab
d = designfilt('lowpassiir', 'FilterOrder', 4, 'HalfPowerFrequency', 50, 'SampleRate', 1000);
t = (0:999)'/1000;  x = sin(2*pi*5*t) + sin(2*pi*200*t);
y = filtfilt(d, x);
max(abs(y - sin(2*pi*5*t)))
```

## See also

[filtfilt](filtfilt) · [fir1](fir1) · [grpdelay](grpdelay) · [impz](impz)
