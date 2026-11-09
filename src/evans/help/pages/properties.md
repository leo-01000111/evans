# properties

The public properties of a class.

## Syntax

    names = properties(obj)
    names = properties('ClassName')
    properties(obj)

## Description

Returns a column cell of the property names a user can read, in the order the class and its superclasses declare them. With no output it prints them. Hidden and private properties are left out.

## Example

The example writes a small class file, `Pt.m`, in the current folder, then asks about an object of it.

```matlab
src = {'classdef Pt < handle', 'properties', 'x = 1;', 'y = 2;', 'end', 'methods', 'function bump(o)', 'o.x = o.x + 1;', 'end', 'end', 'end'};
fid = fopen('Pt.m', 'w'); fprintf(fid, '%s\n', src{:}); fclose(fid);
p = Pt();
properties(p)
```

## See also

[classdef](classdef) · [methods](methods) · [ismethod](ismethod) · [isprop](isprop) · [isvalid](isvalid) · [isobject](isobject) · [addlistener](addlistener) · [notify](notify) · [copy](copy)
