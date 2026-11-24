# audiowrite

Write an array of samples to an audio file.

## Syntax

    audiowrite(filename, y, fs)
    audiowrite(filename, y, fs, 'BitsPerSample', bits)

## Description

`audiowrite` saves `y` as a sound file sampled at `fs` Hz. A vector is one channel; for a matrix each column is a channel and each row a sample.

`'BitsPerSample'` is 8, 16, 24, 32 or 64; the default is 16. At 8, 16 and 24 bits the samples are integers: values are clipped to the range -1 to 1 and scaled, as MATLAB does, so anything outside it is lost. At 32 and 64 bits the file holds floating-point samples and keeps the values as they are.

Only the real part of `y` is written. The folder of `filename` is created if it does not exist. Other options, such as `'Comment'`, are ignored.

Evans writes `.wav` files itself. For another extension, such as `.flac`, the optional `soundfile` Python package has to be installed; without it Evans says that only `.wav` files can be written.

## Example

```matlab
fs = 44100;
t = (0:fs-1)'/fs;
audiowrite('a440.wav', 0.8*sin(2*pi*440*t), fs, 'BitsPerSample', 24);
info = audioinfo('a440.wav')
```

## See also

[audioread](audioread) · [audioinfo](audioinfo) · [sound](sound)
