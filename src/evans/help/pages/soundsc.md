# soundsc

Scale a vector of samples to full volume and play it.

## Syntax

    soundsc(y)
    soundsc(y, fs)

## Description

`soundsc` divides `y` by its largest absolute value, so that the loudest sample reaches full scale, and plays it as [sound](sound) does, at `fs` Hz (8192 when left out). Nothing is changed in `y` itself.

Use it for a signal whose size is not known in advance, such as a filtered recording. A silent signal (all zeros) is played as it is.

Playback returns at once and goes on in the background. If the computer has no audio output, Evans prints one warning and stays silent.

## Example

```matlab
t = (0:7999)'/8000;
y = 0.01*sin(2*pi*440*t);
loudest = max(abs(y/max(abs(y))))
```

A signal this quiet is almost inaudible with `sound(y, 8000)`; scaled first, it plays at full volume:

```
soundsc(y, 8000)
```

## See also

[sound](sound) · [audioread](audioread)
