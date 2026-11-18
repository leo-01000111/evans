# pole

Poles of a dynamic system: the roots of its characteristic polynomial, or the eigenvalues of `A` for a state-space model.

## Syntax

    pole(sys)
    p = pole(sys)

## Description

`p = pole(sys)` returns the poles of `sys`, which can be a `tf`, `zpk` or `ss` model, continuous or discrete. For a transfer function they are the roots of the denominator; for a state-space model they are the eigenvalues of the `A` matrix, so a state-space realisation that is not minimal can show poles a transfer function would cancel. Use [minreal](minreal) first if you want them gone.

The result is a column vector, real when no pole has an imaginary part and complex otherwise, as in MATLAB.

For a continuous system, every pole in the open left half-plane means the system is stable; for a discrete one, every pole inside the unit circle. [isstable](isstable) answers that question directly, and [damp](damp) gives each pole's damping ratio and natural frequency.

## Example

```matlab
s = tf('s');
G = (s + 3) / (s^3 + 2*s^2 + 5*s);
p = pole(G)
max(real(p))
```

## See also

[zero](zero) · [damp](damp) · [pzmap](pzmap) · [isstable](isstable) · [eig](eig)
