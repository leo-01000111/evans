# tic

Start a stopwatch timer, read back with toc.

## Syntax

    tic
    t0 = tic

## Description

`tic` records the current time. A later [toc](toc) reports the seconds elapsed since then. Calling `tic` again restarts the stopwatch, and the time is kept between commands at the console, so you can type `tic` and `toc` on separate lines.

`t0 = tic` returns the current time as a `uint64` timer value instead, and leaves the stopwatch alone: `toc(t0)` measures from that value, so several timings can run at once.

The time includes everything that ran in between, including drawing plots, so time the computation on its own if that is what you want to measure.

## Example

```matlab
tic
G = tf(1, [1 2 1]);
[y, t] = step(G);
toc
```

## See also

[toc](toc) · [fprintf](fprintf)
