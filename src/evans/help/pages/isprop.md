# isprop

Whether an object has a property.

## Syntax

    tf = isprop(obj, name)

## Description

True when `name` is a property of the object's class or a superclass, hidden or not. Fields of a struct are not properties; use `isfield` for those.

## Example

The example writes a small class file, `Pt.m`, in the current folder, then asks about an object of it.

```matlab
src = {'classdef Pt < handle', 'properties', 'x = 1;', 'y = 2;', 'end', 'methods', 'function bump(o)', 'o.x = o.x + 1;', 'end', 'end', 'end'};
fid = fopen('Pt.m', 'w'); fprintf(fid, '%s\n', src{:}); fclose(fid);
p = Pt();
isprop(p, 'x')
isprop(p, 'nope')
```

## See also

[classdef](classdef) · [properties](properties) · [methods](methods) · [ismethod](ismethod) · [isvalid](isvalid) · [isobject](isobject) · [addlistener](addlistener) · [notify](notify) · [copy](copy)
