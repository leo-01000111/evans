# methods

The public methods of a class.

## Syntax

    names = methods(obj)
    methods('ClassName')

## Description

Returns a cell of the method names, including inherited ones and the constructor. With no output it prints them. Hidden and private methods are left out.

## Example

The example writes a small class file, `Pt.m`, in the current folder, then asks about an object of it.

```matlab
src = {'classdef Pt < handle', 'properties', 'x = 1;', 'y = 2;', 'end', 'methods', 'function bump(o)', 'o.x = o.x + 1;', 'end', 'end', 'end'};
fid = fopen('Pt.m', 'w'); fprintf(fid, '%s\n', src{:}); fclose(fid);
p = Pt();
methods(p)
```

## See also

[classdef](classdef) · [properties](properties) · [ismethod](ismethod) · [isprop](isprop) · [isvalid](isvalid) · [isobject](isobject) · [addlistener](addlistener) · [notify](notify) · [copy](copy)
