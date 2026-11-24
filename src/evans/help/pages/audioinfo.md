# audioinfo

Describe an audio file without reading its samples.

## Syntax

    info = audioinfo(filename)

## Description

`audioinfo` returns a struct with these fields:

| Field | Holds |
|---|---|
| `Filename` | the full path of the file |
| `CompressionMethod` | always `'Uncompressed'` |
| `NumChannels` | 1 for mono, 2 for stereo |
| `SampleRate` | the sampling frequency in Hz |
| `TotalSamples` | the number of samples per channel |
| `Duration` | the length in seconds, `TotalSamples / SampleRate` |
| `BitsPerSample` | the stored bit depth |
| `Title`, `Comment`, `Artist` | empty: Evans does not read tags |

Use it to check a file's sampling frequency and length before reading it with [audioread](audioread), or to compare file sizes: the size of a `.wav` file is about `TotalSamples * NumChannels * BitsPerSample / 8` bytes.

## Example

```matlab
t = (0:7999)'/8000;
audiowrite('beep.wav', sin(2*pi*1000*t), 8000);
info = audioinfo('beep.wav');
info.Duration
info.NumChannels
info.BitsPerSample
```

## See also

[audioread](audioread) · [audiowrite](audiowrite)
