# fzero

Find a zero of a function of one variable.

## Syntax

    x = fzero(f, x0)
    x = fzero(f, [a b])
    x = fzero(f, x0, options)
    [x, fval, exitflag, output] = fzero(...)

## Description

`f` is a function handle (or name) taking a scalar and returning a scalar.

With a two-element second argument `[a b]`, `fzero` searches inside that bracket. `f(a)` and `f(b)` must have opposite signs, otherwise it stops with "The function values at the interval endpoints must differ in sign." Only the first two elements are used if you pass more.

With a single starting value `x0`, `fzero` first widens an interval around `x0` by a factor of the square root of 2 at each step until `f` changes sign, then refines the zero with Brent's method (bisection, secant and inverse quadratic interpolation), step for step as MATLAB does. If `x0` is already a zero it is returned at once.

If the search for a sign change fails, `fzero` does not stop with an error: it prints why and returns `x = NaN` and `fval = NaN`, with an `exitflag` that says what happened (below). `fzero(@(x) x^2+1, 1)`, which has no real zero, ends this way once `f` overflows to `Inf`.

`fval` is `f(x)`. `exitflag` is

- `1`: a zero was found.
- `-3`: `f` returned `NaN` or `Inf` during the search for a sign change.
- `-4`: `f` returned a complex value during that search.
- `-5`: the interval shrank to the tolerance and `f` changes sign in it, but `|f(x)|` grew as it shrank, so `x` may be a singular point such as a pole: `fzero(@tan, [1 2])` returns `pi/2` with `exitflag = -5`.
- `-6`: the search widened the interval until it overflowed without finding a sign change, for example for a constant `f`.

`output` is a struct with the fields `intervaliterations` (steps of the search for a sign change, 0 for a bracket), `iterations` (Brent steps), `funcCount` (calls to `f`, counting the search), `algorithm` (`'bisection, interpolation'`) and `message`, the text that the display prints.

Options are set with `optimset`:

- `TolX`: the termination tolerance on `x` (default `eps`). The search stops when the bracket is narrower than about `2*TolX*max(abs(x), 1)`, so `optimset('TolX', 1e-3)` gives a coarser zero with fewer calls to `f`.
- `Display`: `'notify'` (the default) prints the message only when `fzero` fails (`exitflag` not 1); `'final'` and `'iter'` always print it; `'off'` or `'none'` print nothing. `'iter'` does not print a table of iterations.

Limits of Evans: `OutputFcn`, `PlotFcns` and `FunValCheck` are not supported, so `exitflag` is never `-1`.

`fzero` returns one zero; use [roots](roots) for all zeros of a polynomial.

## Example

```matlab
x = fzero(@cos, [1 2])
[x, fval, flag, out] = fzero(@(x) x^2 - 2, 1)
```

The first call gives 1.5708. The second gives 1.4142 with `flag` equal to 1; `out.intervaliterations` is 9 and `out.message` is `'Zero found in the interval [0.547452, 1.45255]'`.

## See also

[fminsearch](fminsearch) · [fsolve](fsolve) · [fminunc](fminunc) · [roots](roots)
