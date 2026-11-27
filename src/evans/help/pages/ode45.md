# ode45

Solve an ordinary differential equation `y' = f(t, y)` with a Runge-Kutta method of orders 4 and 5.

## Syntax

    [t, y] = ode45(f, tspan, y0)
    [t, y] = ode45(f, tspan, y0, options)
    sol = ode45(f, tspan, y0)
    ode45(f, tspan, y0)

## Description

`f` is a function handle taking `(t, y)` and returning the derivative as a column vector the same size as `y0`. `tspan` is `[t0 tf]`, or a longer vector of the times you want back. `y0` holds the initial values. Evans passes `f` a scalar `y` when the system has one state, and a column vector otherwise.

With a two-element `tspan`, `t` is the solver's own steps with three extra interpolated points between each pair of steps. With more than two elements, `t` is exactly `tspan`. Either way `y` has one row per time and one column per state. A decreasing `tspan` such as `[1 0]` integrates backwards.

`options` comes from `odeset`. Evans reads only `RelTol` (default `1e-3`), `AbsTol` (default `1e-6`, a scalar or one value per state), `MaxStep` and `InitialStep`; `Events`, `Mass`, `Jacobian` and every other field are not supported: when one is set, `ode45` prints a warning naming it and solves without it.

With one output, `sol = ode45(...)` returns a struct with the fields `solver` (the text `'ode45'`), `x` (the solver's steps, a row, with no interpolated points) and `y` (one row per state, one column per step). There is no `deval`. With no output, `ode45` draws the solution in a figure.

Extra parameters after `options` are not passed on to `f`; wrap them in the handle instead: `@(t,y) f(t,y,a)`. A third output (`[t,y,te] = ...`) gives "Too many output arguments."

If the solver fails, for instance on a solution that blows up in finite time, Evans prints "Warning: ode45: ..." and returns what it had reached. A `tspan` with fewer than two elements stops with "The time span must have at least two elements."

`ode23`, `ode15s` and `ode23s` exist too, with the same syntax, options and outputs, backed by the Bogacki-Shampine, BDF and Radau methods of scipy. They return only the solver's steps, with no interpolated points. `ode113` and `ode23t` do not exist.

## Example

```matlab
[t, y] = ode45(@(t,y) -2*y, [0 0.5 1], 1);
disp([t y])
opts = odeset('RelTol', 1e-8, 'AbsTol', 1e-10);
[t, y] = ode45(@(t,y) -2*y, [0 1], 1, opts);
y(end) - exp(-2)
```

The first call returns the solution at the three requested times: 1, 0.3681 and 0.1355. The tight tolerances bring the error at `t = 1` down to about 6e-10.

## See also

[fzero](fzero) · [integral](integral) · [lsim](lsim)
