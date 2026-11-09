# remove

Delete keys from a map.

## Syntax

    remove(m, key)
    remove(m, {k1, k2})

## Description

Deletes the key or keys from the map, which is changed in place. A missing key is an error.

## Example

```matlab
m = containers.Map({'a', 'b'}, [1 2]);
remove(m, 'a');
m.Count
```

## See also

[containers](containers) · [isKey](isKey) · [keys](keys)
