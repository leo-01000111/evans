# fzero

Find a zero of a function of one variable.

## Syntax

    x = fzero(f, x0)
    x = fzero(f, [a b])
    [x, fval, exitflag, output] = fzero(f, x0)

## Description

`f` is a function handle (or name) taking a scalar and returning a scalar. A function that returns a vector stops with "The function must return a scalar value".

With a two-element second argument `[a b]`, `fzero` searches inside that bracket. `f(a)` and `f(b)` must have opposite signs, otherwise it stops with "The function values at the interval endpoints must differ in sign." Only the first two elements are used if you pass more.

With a single starting value `x0`, `fzero` first widens an interval around `x0` by a factor of the square root of 2 at each step until `f` changes sign, then refines the zero with Brent's method. If `f` returns `NaN` or `Inf` during that search, it stops with "Exiting fzero: aborting search for an interval containing a sign change because NaN or Inf function value encountered during search." If `x0` is already a zero it is returned at once.

`fval` is `f(x)`. `exitflag` is always `1`, and `output` is a struct with the single field `algorithm`, the text `'bisection, interpolation'`; it has no iteration or function counts.

The options argument (for example `optimset('TolX', 1e-3)`) is accepted but ignored: the zero is always found to about machine precision.

Some failures are reported by the underlying solver rather than by an `fzero` message. `fzero(@(x) x^2+1, 1)` ends with the text "(34, 'Result too large')", and `fzero(@(x) 1/x, 1)`, whose sign change is a pole, ends with "Failed to converge after 500 iterations." `fzero` returns one zero; use `roots` for a polynomial.

## Example

```matlab
x = fzero(@cos, [1 2])
[x, fval, flag] = fzero(@(x) x^3 - 2, 1)
```

The first call gives 1.5708. The second gives 1.2599, the cube root of 2, with `fval` printed as 0 and `flag` equal to 1.

## See also

[fminsearch](fminsearch) · [fsolve](fsolve) · [fminunc](fminunc) · [roots](roots)
