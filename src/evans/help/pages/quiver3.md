# quiver3

Draw arrows in 3-D.

## Syntax

    quiver3(X, Y, Z, U, V, W)
    quiver3(Z, U, V, W)
    quiver3(..., scale)

## Description

`quiver3(X, Y, Z, U, V, W)` draws an arrow at each point `(X(i), Y(i), Z(i))` along `(U(i), V(i), W(i))`, scaled as [quiver](quiver) scales its arrows.

## Example

```matlab
quiver3(zeros(3, 1), zeros(3, 1), zeros(3, 1), [1; 0; 0], [0; 1; 0], [0; 0; 1], 0)
```

## See also

[quiver](quiver) · [plot3](plot3)
