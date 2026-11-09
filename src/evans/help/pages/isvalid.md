# isvalid

Whether a handle object is still usable.

## Syntax

    tf = isvalid(h)

## Description

A handle object stops being valid when `delete(h)` runs; every name that holds it sees that. A value object is always valid. Anything that is not a class object gives false.

## Example

The example writes a small class file, `Pt.m`, in the current folder, then asks about an object of it.

```matlab
src = {'classdef Pt < handle', 'properties', 'x = 1;', 'y = 2;', 'end', 'methods', 'function bump(o)', 'o.x = o.x + 1;', 'end', 'end', 'end'};
fid = fopen('Pt.m', 'w'); fprintf(fid, '%s\n', src{:}); fclose(fid);
p = Pt();
isvalid(p)
delete(p)
isvalid(p)
```

## See also

[classdef](classdef) · [properties](properties) · [methods](methods) · [ismethod](ismethod) · [isprop](isprop) · [isobject](isobject) · [addlistener](addlistener) · [notify](notify) · [copy](copy)
