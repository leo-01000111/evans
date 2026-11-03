# optimoptions

Options for an optimisation solver.

## Syntax

    options = optimoptions(solver)
    options = optimoptions(solver, Name, Value, ...)
    options = optimoptions(oldoptions, Name, Value, ...)

## Description

`solver` is the solver's name, such as `'fmincon'` or `'lsqcurvefit'`. The options Evans reads are `'Display'` (`'off'`, `'final'`, `'iter'`), `'MaxIterations'`, `'MaxFunctionEvaluations'`, `'OptimalityTolerance'`, `'StepTolerance'`, `'FunctionTolerance'` and `'SpecifyObjectiveGradient'`; the old names (`'TolFun'`, `'MaxIter'`) work too. An option the solver does not know stops with an error.

Pass the result as the solver's `options` argument.

## Example

```matlab
opts = optimoptions('fminunc', 'Display', 'off');
x = fminunc(@(x) (x - 2).^2 + 1, 0, opts)
```

## See also

[fminunc](fminunc) · [fmincon](fmincon) · [lsqcurvefit](lsqcurvefit)
