# simplify

Simplest form of a symbolic expression.

## Syntax

    g = simplify(f)

## Description

`simplify(f)` tries cancelling, combining and rewriting, and returns the shortest equivalent form it finds: `(s^2 - 1)/(s + 1)` becomes `s - 1`, and `sin(x)^2 + cos(x)^2` becomes `1`.

The answer depends on what is known about the variables. `sqrt(x^2)` stays as it is for a general `x`, which could be negative or complex, and becomes `x` after `syms x positive`.

"Simplest" is not always the form you want. [expand](expand) multiplies out, [factor](factor) does the opposite, `collect` groups by powers of one variable, and [partfrac](partfrac) splits into simple fractions. Options such as `'Steps'` are accepted and ignored.

## Example

```matlab
syms s
simplify((s^2 - 1)/(s + 1))
A = [0 1; -2 -3];
simplify(inv(s*eye(2) - A))
```

## See also

[expand](expand) · [factor](factor) · [partfrac](partfrac) · [subs](subs)
