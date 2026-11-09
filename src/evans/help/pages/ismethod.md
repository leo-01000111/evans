# ismethod

Whether an object has a method.

## Syntax

    tf = ismethod(obj, name)

## Description

True when `name` is a public method of the object's class or a superclass. It is false for properties and for anything that is not a class object.

## Example

The example writes a small class file, `Pt.m`, in the current folder, then asks about an object of it.

```matlab
src = {'classdef Pt < handle', 'properties', 'x = 1;', 'y = 2;', 'end', 'methods', 'function bump(o)', 'o.x = o.x + 1;', 'end', 'end', 'end'};
fid = fopen('Pt.m', 'w'); fprintf(fid, '%s\n', src{:}); fclose(fid);
p = Pt();
ismethod(p, 'bump')
```

## See also

[classdef](classdef) · [properties](properties) · [methods](methods) · [isprop](isprop) · [isvalid](isvalid) · [isobject](isobject) · [addlistener](addlistener) · [notify](notify) · [copy](copy)
