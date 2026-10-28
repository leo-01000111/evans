# rng

Seed or save the random number generator used by rand, randn, randi and randperm.

## Syntax

    rng(seed)
    rng('default')
    rng('shuffle')
    rng(seed, 'twister')
    s = rng
    rng(s)

## Description

`rng(seed)` seeds the generator with a non-negative integer below 2^32, so that what follows repeats: `rng(1); a = rand; rng(1); b = rand;` gives `a == b`. `rng('default')` is seed 0; `rng('shuffle')` seeds from the clock.

`s = rng` returns the current settings as a struct with fields `Type`, `Seed` and `State`, and `rng(s)` restores them, so the stream continues from where `s` was taken. `sprev = rng(seed)` returns the settings before the change.

Evans uses numpy's Mersenne Twister. Seeding makes Evans reproducible, but the numbers are not the ones MATLAB draws for the same seed. Only the `'twister'` generator is supported.

## Example

```matlab
rng(7);
a = rand(1, 3);
rng(7);
b = rand(1, 3);
all(a == b)
```

## See also

[rand](rand) · [randi](randi) · [randperm](randperm)
