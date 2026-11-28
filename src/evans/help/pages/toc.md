# toc

Seconds elapsed since the last tic.

## Syntax

    toc
    elapsed = toc
    elapsed = toc(t0)

## Description

`toc` with no output prints `Elapsed time is ... seconds.`, with six decimals. `elapsed = toc` returns the time in seconds as a number and prints nothing, so you can store it or format it with [fprintf](fprintf).

`toc` does not stop the stopwatch: each call measures from the same [tic](tic), until `tic` runs again. Without any `tic`, `toc` counts from when the console started.

`toc(t0)` measures from the timer value `t0 = tic` returned instead of from the last plain `tic`; anything other than such a value is an error.

## Example

```matlab
tic
for k = 1:50
    p = pole(tf(k, [1 2 k]));
end
elapsed = toc;
fprintf('Under 10 s: %d\n', elapsed < 10)
```

## See also

[tic](tic) · [fprintf](fprintf) · [disp](disp)
