# audioread

Read an audio file into an array of samples.

## Syntax

    y = audioread(filename)
    [y, fs] = audioread(filename)
    [y, fs] = audioread(filename, [start stop])
    [y, fs] = audioread(filename, 'native')

## Description

`audioread` reads a sound file and returns the samples `y` as a matrix with one row per sample and one column per channel (a mono file gives a column vector). With `fs` it also returns the sampling frequency in Hz.

Samples are `double` values between -1 and 1, whatever the file's bit depth. The time of sample `n` is `(n-1)/fs`.

`[start stop]` reads only those samples, counted from 1. `stop` may be `Inf` for the end of the file.

`'native'` returns the integers stored in the file instead (`uint8`, `int16` or `int32` for PCM files) and leaves them unscaled.

A relative `filename` is taken from the folder of the script that is running (the current folder at the prompt), so a script finds a sound saved beside it. A file that is not there stops with "The filename specified was not found".

Evans reads `.wav` files itself: 8, 16, 24 and 32-bit PCM, and 32 and 64-bit floating point. Other formats (FLAC, OGG) are read when the optional `soundfile` Python package is installed; without it Evans says the file is not a WAVE file it understands.

## Example

```matlab
fs = 8000;
t = (0:fs-1)'/fs;
y = 0.5*sin(2*pi*440*t);
audiowrite('tone.wav', y, fs);
[z, fs2] = audioread('tone.wav');
size(z)
fs2
max(abs(z - y))
```

The last line is about 1.5e-5, half a step of 16-bit audio (1/32768): the samples were rounded when they were written.

## See also

[audiowrite](audiowrite) · [audioinfo](audioinfo) · [sound](sound)
