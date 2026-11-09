# values

The values of a map.

## Syntax

    v = values(m)
    v = values(m, {k1, k2})

## Description

A row cell of the values, in key order, or those of the keys given.

## Example

```matlab
m = containers.Map({'b', 'a'}, [2 1]);
values(m)
values(m, {'b'})
```

## See also

[containers](containers) · [isKey](isKey) · [keys](keys)
