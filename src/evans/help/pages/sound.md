# sound

Play a vector of samples through the speakers.

## Syntax

    sound(y)
    sound(y, fs)

## Description

`sound` plays `y` at the sampling frequency `fs` in Hz (8192 when left out). It returns at once and the sound plays in the background, so a script goes on while it plays.

`y` is a vector for one channel, or a matrix with one column per channel. Samples are expected between -1 and 1; anything outside is clipped, which is audible as distortion. To scale the signal to fit first, use [soundsc](soundsc).

Playback uses the `sounddevice` package if it is installed and otherwise the audio support that comes with Evans (Qt Multimedia, then the system player on Windows and macOS). If the computer has no audio output, Evans prints one warning and the following calls are silent rather than failing.

`sound` does not wait for the end of the sound and has no stop command.

## Example

```matlab
fs = 8000;
t = (0:2*fs-1)'/fs;
y = 0.3*sin(2*pi*440*t);
duration = numel(y)/fs
```

Then play it:

```
sound(y, fs)
```

This plays two seconds of an A, and the script goes on at once.

## See also

[soundsc](soundsc) · [audioread](audioread) · [audiowrite](audiowrite)
