# containers

containers.Map: a lookup table from keys to values.

## Syntax

    m = containers.Map
    m = containers.Map(keys, values)
    m = containers.Map('KeyType', kt, 'ValueType', vt)

## Description

A `containers.Map` pairs keys, all text or all numbers, with values of any kind. It is a handle: `n = m` is the same map, and a change through one name shows through the other. Keys come back sorted, text by character code and numbers ascending.

- `m(key)` reads and `m(key) = v` sets or adds a value. A missing key is an error.
- `m.Count`, `m.KeyType`, `m.ValueType`; `length(m)` and `numel(m)` give the count.
- `keys(m)`, `values(m)`, `values(m, {k1, k2})`, `isKey(m, k)` and `remove(m, k)`, also written `m.keys()` and so on.
- `containers.Map(keysCell, valuesCell)` builds one from a cell of keys and a cell (or numeric array) of values. A single key is `containers.Map('a', 1)`. `'UniformValues', false` forces `ValueType` `any`.

Key types other than text and double (`int32` and so on) are stored as doubles, since Evans has no integer types yet.

## Example

```matlab
m = containers.Map();
m('speed') = 3;
m('mass') = 12;
keys(m)
values(m)
isKey(m, 'mass')
m2 = containers.Map({'x', 'y'}, [10 20]);
m2('y')
```

## See also

[isKey](isKey) · [keys](keys) · [values](values) · [remove](remove) · [struct2cell](struct2cell)
