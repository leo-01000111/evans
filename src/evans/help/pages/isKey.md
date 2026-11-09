# isKey

Test for a key in a map.

## Syntax

    tf = isKey(m, key)
    tf = isKey(m, {k1, k2})

## Description

True where the map has the key. A cell of keys gives a logical array. A key of the wrong type is simply not there.

## Example

```matlab
m = containers.Map({'a'}, {1});
isKey(m, {'a', 'z'})
```

## See also

[containers](containers) · [keys](keys) · [values](values)
